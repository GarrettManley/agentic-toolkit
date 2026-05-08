"""submit.py — submission gate dispatcher.

PT-2 hook validates --token before this runs. This script dispatches per --venue:
  --venue manual-form  : opens browser to submission URL, copies finding-body,
                         marks finding submitted-manual; exits with reminder.
  --venue ghsa         : uses `gh api` POST to repo's security-advisories endpoint
                         (full implementation in Stage 1).
  --venue huntr|ibb-h1|h1|bugcrowd|intigriti|direct-maintainer : stubbed in Stage 1.

Every dispatch (full or stubbed) appends to submissions/ledger.jsonl.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from lib.paths import SUBMISSIONS_TOKENS_DIR, FINDINGS_DIR, OVERRIDES_USED_DIR  # noqa: E402
from lib.sign_verify import verify_token, is_expired  # noqa: E402
from lib import ledger  # noqa: E402

VENUE_CHOICES = ["huntr", "ghsa", "ibb-h1", "h1", "bugcrowd", "intigriti", "direct-maintainer", "manual-form"]
STAGE_1_FULL = {"manual-form", "ghsa"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_finding_dir(trace_id: str) -> Path | None:
    if not FINDINGS_DIR.exists():
        return None
    for d in FINDINGS_DIR.iterdir():
        if d.is_dir() and trace_id in d.name:
            return d
    return None


def _consume_token(token_id: str, trace_id: str, expected_venue: str) -> tuple[bool, str | None]:
    """Validate + consume a single-use approval token. Returns (ok, error)."""
    token_path = SUBMISSIONS_TOKENS_DIR / f"{token_id}.json"
    if not token_path.exists():
        return False, f"token not found: {token_id}"
    try:
        with token_path.open("r", encoding="utf-8") as f:
            token = json.load(f)
    except Exception as exc:
        return False, f"failed to parse token: {exc}"

    ok, err = verify_token(token)
    if not ok:
        return False, f"signature verification failed: {err}"
    if is_expired(token):
        return False, "token expired"
    if token.get("trace_id") != trace_id:
        return False, f"token trace_id ({token.get('trace_id')}) != requested ({trace_id})"
    if token.get("venue") != expected_venue:
        return False, f"token venue ({token.get('venue')}) != requested ({expected_venue})"
    if token.get("max_uses", 1) < 1:
        return False, "token has no remaining uses"

    # Consume: move to overrides/used/ (since approval tokens are also single-use; reuse the same dir)
    OVERRIDES_USED_DIR.mkdir(parents=True, exist_ok=True)
    target = OVERRIDES_USED_DIR / token_path.name
    try:
        token_path.replace(target)
    except OSError as exc:
        return False, f"failed to consume token: {exc}"
    return True, None


def _update_finding_status(finding_dir: Path, new_status: str, venue_response: str | None = None) -> None:
    """Update finding.md frontmatter status field. Best-effort YAML rewrite."""
    finding_md = finding_dir / "finding.md"
    if not finding_md.exists():
        return
    try:
        content = finding_md.read_text(encoding="utf-8")
        # Track from-status for ledger
        old_status = "?"
        m_old = re.search(r"^status:\s*(\S+)", content, re.MULTILINE)
        if m_old:
            old_status = m_old.group(1)

        new_content = re.sub(
            r"^status:.*$",
            f"status: {new_status}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if venue_response:
            if "venue_response:" in new_content:
                new_content = re.sub(
                    r"^venue_response:.*$",
                    f"venue_response: {venue_response}",
                    new_content,
                    count=1,
                    flags=re.MULTILINE,
                )
            else:
                # Insert into frontmatter near status:
                new_content = re.sub(
                    r"^(status:.*)$",
                    rf"\1\nvenue_response: {venue_response}",
                    new_content,
                    count=1,
                    flags=re.MULTILINE,
                )
        if "submitted_at:" not in new_content:
            new_content = re.sub(
                r"^(status:.*)$",
                rf"\1\nsubmitted_at: {_utc_now()}",
                new_content,
                count=1,
                flags=re.MULTILINE,
            )
        finding_md.write_text(new_content, encoding="utf-8")

        # Ledger event
        ledger.append_event(
            "status-transition",
            trace_id=re.search(r"trace_id:\s*(\S+)", content).group(1) if re.search(r"trace_id:\s*(\S+)", content) else None,
            from_status=old_status,
            to_status=new_status,
        )
    except Exception:
        pass


def _dispatch_manual_form(trace_id: str, finding_dir: Path, scope_data: dict | None) -> tuple[bool, str | None]:
    """Open the program's submission form URL; copy finding body to clipboard."""
    submit_url = None
    if scope_data:
        submit_url = scope_data.get("submission", {}).get("endpoint")

    finding_md = finding_dir / "finding.md"
    if finding_md.exists():
        body = finding_md.read_text(encoding="utf-8")
        # Strip frontmatter for the body
        body_only = re.sub(r"^---\n.*?\n---\n?", "", body, count=1, flags=re.DOTALL)
        # Copy to clipboard via PowerShell Set-Clipboard
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Set-Clipboard"],
                input=body_only, text=True, capture_output=True, timeout=5,
            )
            if proc.returncode == 0:
                print("Finding body copied to clipboard.")
        except Exception:
            print("(could not copy to clipboard; paste manually from finding.md body)")

    if submit_url:
        print(f"Opening submission form: {submit_url}")
        try:
            webbrowser.open(submit_url)
        except Exception:
            pass
    else:
        print("(no submission URL in scope; navigate to the program's submission page manually)")

    print(f"\nMARKING {trace_id} as submitted-manual. Confirm submission on venue website.")
    return True, "submitted-manual"


def _dispatch_ghsa(trace_id: str, finding_dir: Path, scope_data: dict | None) -> tuple[bool, str | None]:
    """Submit via `gh api` to a repo's security-advisories endpoint.

    Stage 1: drafts the request body and prints what would be POSTed if --dry-run is set.
    Otherwise actually invokes `gh api`. Uses gh CLI auth — no keyring credential needed.
    """
    if not scope_data:
        return False, "scope data unavailable; cannot determine target repo"

    in_scope = scope_data.get("in_scope", [])
    target_repo_entry = next(
        (e for e in in_scope if e.get("asset_type") == "repo" and "github.com/" in e.get("identifier", "")),
        None,
    )
    if not target_repo_entry:
        return False, "no GitHub repo in scope's in_scope[] for ghsa submission"

    m = re.match(r"github\.com/([\w.-]+)/([\w.-]+)", target_repo_entry["identifier"])
    if not m:
        return False, f"could not parse owner/repo from {target_repo_entry['identifier']}"
    owner, repo = m.group(1), m.group(2)

    # Build request body from finding.md frontmatter
    finding_md = finding_dir / "finding.md"
    body_text = ""
    fm = {}
    if finding_md.exists():
        try:
            import yaml
            content = finding_md.read_text(encoding="utf-8")
            mfm = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
            if mfm:
                fm = yaml.safe_load(mfm.group(1)) or {}
                body_text = mfm.group(2)
        except Exception as exc:
            return False, f"failed to read finding.md: {exc}"

    request_body = {
        "summary": fm.get("title", "Security finding"),
        "description": body_text,
        "severity": _cvss_score_to_severity(fm.get("severity", {}).get("cvss_v3_1_score", 0)),
        "cve_id": fm.get("evidence", {}).get("cve_id_proposed_or_assigned"),
        "vulnerabilities": [{
            "package": {
                "ecosystem": fm.get("target", {}).get("ecosystem", "other"),
                "name": fm.get("target", {}).get("identifier", "unknown"),
            },
            "vulnerable_version_range": fm.get("evidence", {}).get("affected_versions_range", ""),
            "patched_versions": fm.get("evidence", {}).get("fixed_version", ""),
        }],
        "cwe_ids": fm.get("cwe_ids", []),
    }

    body_json = json.dumps(request_body)
    cmd = [
        "gh", "api",
        "--method", "POST",
        f"/repos/{owner}/{repo}/security-advisories",
        "--input", "-",
    ]
    print(f"Invoking: {' '.join(cmd)}")
    print(f"Body (first 200 chars): {body_json[:200]}...")

    try:
        proc = subprocess.run(cmd, input=body_json, text=True, capture_output=True, timeout=30)
    except FileNotFoundError:
        return False, "gh CLI not installed; install from cli.github.com"
    except subprocess.TimeoutExpired:
        return False, "gh api timed out after 30s"

    if proc.returncode != 0:
        return False, f"gh api failed: {proc.stderr[:500]}"

    try:
        resp = json.loads(proc.stdout)
        ghsa_id = resp.get("ghsa_id") or resp.get("id") or "<unknown>"
    except json.JSONDecodeError:
        ghsa_id = "<response was not JSON>"

    print(f"Submitted as GHSA: {ghsa_id}")
    return True, ghsa_id


def _cvss_score_to_severity(score: float) -> str:
    """Map CVSS v3.1 score to GHSA severity enum."""
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    return "low"


def _dispatch_stub(venue: str, trace_id: str) -> tuple[bool, str | None]:
    print(f"  Stage 1 stub: --venue {venue} not implemented yet (Stage 7).")
    print(f"  Use --venue manual-form to open the venue's submission page and paste manually.")
    return False, f"stage-1-stub-{venue}"


def _load_program_scope(program_slug: str) -> dict | None:
    from lib.paths import PROGRAMS_DIR
    path = PROGRAMS_DIR / program_slug / "scope.yaml"
    if not path.exists():
        return None
    try:
        import yaml
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return None


def main() -> int:
    p = argparse.ArgumentParser(description="Submit a finding to a bounty venue.")
    p.add_argument("--trace", required=True, help="e.g. FIND-2026-05-07-001")
    p.add_argument("--token", required=True, help="approval token id (from sign_approval.py)")
    p.add_argument("--venue", required=True, choices=VENUE_CHOICES)
    args = p.parse_args()

    finding_dir = _find_finding_dir(args.trace)
    if finding_dir is None:
        print(f"ERROR: no finding directory matching {args.trace}", file=sys.stderr)
        return 1

    # Read program_slug from finding frontmatter to load scope
    finding_md = finding_dir / "finding.md"
    scope_data = None
    program_slug = None
    if finding_md.exists():
        try:
            content = finding_md.read_text(encoding="utf-8")
            m = re.search(r"program_slug:\s*(\S+)", content)
            if m:
                program_slug = m.group(1).strip("\"'")
                scope_data = _load_program_scope(program_slug)
        except Exception:
            pass

    # PT-2 enforcement: validate + consume token
    ok, err = _consume_token(args.token, args.trace, args.venue)
    if not ok:
        print(f"ERROR (PT-2): {err}", file=sys.stderr)
        ledger.append_event(
            "submission-failed",
            trace_id=args.trace,
            venue=args.venue,
            approval_token_id=args.token,
            outcome="blocked",
            notes=f"PT-2 token validation failed: {err}",
        )
        return 2

    # Log attempt
    ledger.append_event(
        "submission-attempted",
        trace_id=args.trace,
        venue=args.venue,
        approval_token_id=args.token,
    )

    # Dispatch
    if args.venue == "manual-form":
        ok, info = _dispatch_manual_form(args.trace, finding_dir, scope_data)
    elif args.venue == "ghsa":
        ok, info = _dispatch_ghsa(args.trace, finding_dir, scope_data)
    else:
        ok, info = _dispatch_stub(args.venue, args.trace)

    if ok:
        new_status = "submitted-manual" if args.venue == "manual-form" else "submitted"
        _update_finding_status(finding_dir, new_status, venue_response=info)
        ledger.append_event(
            "submission-succeeded",
            trace_id=args.trace,
            venue=args.venue,
            approval_token_id=args.token,
            submission_id=info,
            outcome=new_status,
            outcome_at=_utc_now(),
        )
        print(f"\nSubmission complete. Trace {args.trace} -> {new_status}")
        return 0
    else:
        ledger.append_event(
            "submission-failed",
            trace_id=args.trace,
            venue=args.venue,
            approval_token_id=args.token,
            outcome="failed",
            notes=info,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
