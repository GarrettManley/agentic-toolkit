"""verify_finding.py — pre-commit and pre-submit validator.

Runs:
1. Schema validation against finding.schema.json (frontmatter + class-keyed evidence)
2. PoC reproduction in sandbox (or sandbox-equivalent for Stage 1)
3. Reference validation (CVE/pkg@version/commit-SHA)
4. Evidence completeness (timeline.md, redacted/, etc.)

Writes machine-readable result to findings/<trace>/verification.json.
Exits 0 on success, non-zero on any failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add hooks/ to path for lib imports
HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from lib.paths import FINDINGS_DIR, SCHEMA_DIR, RUNTIME_SANDBOX_DIR  # noqa: E402
from lib.schema_validate import validate_finding_frontmatter, validate_evidence  # noqa: E402
from lib.nvd_lookup import validate_cve_ids_in_text  # noqa: E402
from lib.registry_lookup import extract_pkg_versions, version_exists  # noqa: E402
from lib.git_lookup import extract_repo_sha_pairs_from_text, commit_exists  # noqa: E402
from sandbox.runner import sandbox_run, SandboxError  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Extract YAML frontmatter and body. Returns (frontmatter_dict, body).
    Uses PyYAML if available; otherwise raises with install hint."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
    if not m:
        return None, content
    fm_text = m.group(1)
    body = m.group(2)
    try:
        import yaml
        fm = yaml.safe_load(fm_text)
    except ImportError:
        raise RuntimeError("PyYAML not installed. Run: pip install pyyaml (or uv add pyyaml).")
    return fm, body


def _find_finding_dir(trace_id: str) -> Path | None:
    """Locate findings/YYYY-MM-DD-<trace>-<slug>/ directory by trace_id."""
    if not FINDINGS_DIR.exists():
        return None
    for d in FINDINGS_DIR.iterdir():
        if not d.is_dir():
            continue
        if trace_id in d.name:
            return d
    return None


def run_poc_in_sandbox(*, workdir: Path, ecosystem: str, expected_exit_code: int,
                       deterministic: bool, expected_hash: str | None,
                       timeout: int = 120) -> tuple[bool, str]:
    """Run reproduce.sh inside the Docker sandbox. Returns (ok, message).

    The mount is confined to the poc/ subdirectory (workdir); sibling dirs
    (evidence/, timeline.md, finding.md) are never mounted into the container,
    preventing an untrusted PoC from tampering with its own evidence.

    v1: one-pass with network (install+trigger together) — the immutable finding
    contract. phase='install' so the registry is reachable; host-isolation provides
    containment. Fails closed on SandboxError (no host fallback)."""
    if not (workdir / "reproduce.sh").exists():
        return False, "poc/reproduce.sh not found"
    try:
        res = sandbox_run(["bash", "reproduce.sh"], ecosystem=ecosystem,
                          phase="install", workdir_host=workdir, timeout=timeout)
    except SandboxError as e:
        return False, f"sandbox unavailable: {e}"

    if res.timed_out:
        return False, f"PoC timed out after {timeout}s"
    if res.exit_code != expected_exit_code:
        return False, f"PoC exit {res.exit_code} != expected {expected_exit_code}"
    if deterministic and not expected_hash:
        return False, "deterministic=true but no expected_output_hash declared"
    if deterministic and res.stdout_sha256 != expected_hash:
        return False, f"PoC stdout hash {res.stdout_sha256} != expected {expected_hash}"
    return True, "PoC reproduced successfully"


def verify(trace_id: str, *, run_poc: bool = True) -> tuple[bool, dict]:
    """Run all checks. Returns (ok, result_dict)."""
    result: dict = {
        "trace_id": trace_id,
        "verified_at": _utc_now(),
        "checks": [],
        "ok": False,
    }

    # Locate finding
    finding_dir = _find_finding_dir(trace_id)
    if finding_dir is None:
        result["checks"].append({"name": "locate", "ok": False, "error": f"no finding dir matching {trace_id}"})
        return False, result
    result["finding_dir"] = str(finding_dir)

    finding_md = finding_dir / "finding.md"
    if not finding_md.exists():
        result["checks"].append({"name": "locate", "ok": False, "error": "finding.md missing"})
        return False, result

    # Parse frontmatter
    content = finding_md.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(content)
    if fm is None:
        result["checks"].append({"name": "frontmatter", "ok": False, "error": "no YAML frontmatter found"})
        return False, result
    result["checks"].append({"name": "frontmatter-parse", "ok": True})

    # Schema validate frontmatter
    ok, errors = validate_finding_frontmatter(fm)
    result["checks"].append({"name": "schema-frontmatter", "ok": ok, "errors": errors})
    if not ok:
        return False, result

    # CVE validation
    cve_failures = validate_cve_ids_in_text(content)
    result["checks"].append({
        "name": "cve-references",
        "ok": not cve_failures,
        "failures": cve_failures,
    })
    if cve_failures:
        return False, result

    # Package@version validation
    pkg_failures = []
    for pkg, ver in extract_pkg_versions(content):
        confirmed = False
        for ecosystem in ("npm", "pypi", "cargo", "rubygems"):
            try:
                ok2, _ = version_exists(ecosystem, pkg, ver)
                if ok2:
                    confirmed = True
                    break
            except NotImplementedError:
                continue
        if not confirmed:
            pkg_failures.append(f"{pkg}@{ver}")
    result["checks"].append({
        "name": "package-references",
        "ok": not pkg_failures,
        "failures": pkg_failures,
    })
    if pkg_failures:
        return False, result

    # Commit SHA validation
    sha_failures = []
    for owner, repo, sha in extract_repo_sha_pairs_from_text(content):
        ok2, err = commit_exists(owner, repo, sha)
        if not ok2:
            sha_failures.append(f"github.com/{owner}/{repo}@{sha}: {err}")
    result["checks"].append({
        "name": "commit-references",
        "ok": not sha_failures,
        "failures": sha_failures,
    })
    if sha_failures:
        return False, result

    # Class-specific evidence schema validation
    vuln_class = fm.get("vuln_class", "")
    evidence_data = fm.get("evidence_class_specific", {})
    # If evidence_class_specific is not in frontmatter, look for it as a top-level key
    # under evidence (per Stage 1 convention; Stage 4+ may refine this layout)
    if not evidence_data:
        # Check if top-level frontmatter keys match the class schema's required fields
        # (allowing the class fields to live at top level too)
        evidence_data = fm
    ok, errors = validate_evidence(vuln_class, evidence_data) if vuln_class else (False, ["missing vuln_class"])
    result["checks"].append({"name": "schema-evidence", "ok": ok, "errors": errors})
    if not ok:
        return False, result

    # Evidence files
    timeline_md = finding_dir / "timeline.md"
    redacted_dir = finding_dir / "evidence" / "redacted"
    poc_script = finding_dir / "poc" / "reproduce.sh"
    evidence_ok = timeline_md.exists() and redacted_dir.exists() and poc_script.exists()
    missing = [str(p) for p in (timeline_md, redacted_dir, poc_script) if not p.exists()]
    result["checks"].append({
        "name": "evidence-files",
        "ok": evidence_ok,
        "missing": missing,
    })
    if not evidence_ok:
        return False, result

    # PoC reproduction
    if run_poc:
        ecosystem = (fm.get("target") or {}).get("ecosystem")
        if not ecosystem:
            result["checks"].append({
                "name": "poc-reproduction", "ok": False,
                "message": "finding has no target.ecosystem — sandbox needs it",
            })
            return False, result
        poc_meta = fm.get("poc", {})
        expected_exit = int(poc_meta.get("expected_exit_code", 0))
        deterministic = bool(poc_meta.get("deterministic", False))
        expected_hash = poc_meta.get("expected_output_hash")
        ok, msg = run_poc_in_sandbox(workdir=finding_dir / "poc", ecosystem=ecosystem,
                                     expected_exit_code=expected_exit,
                                     deterministic=deterministic,
                                     expected_hash=expected_hash)
        result["checks"].append({"name": "poc-reproduction", "ok": ok, "message": msg})
        if not ok:
            return False, result

    result["ok"] = True
    return True, result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a sec-research finding.")
    parser.add_argument("trace_id", help="e.g. FIND-2026-05-07-001")
    parser.add_argument("--no-poc", action="store_true", help="Skip PoC reproduction (faster; for syntax checks only)")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    ok, result = verify(args.trace_id, run_poc=not args.no_poc)

    # Persist verification.json
    fd = result.get("finding_dir")
    if fd:
        try:
            with (Path(fd) / "verification.json").open("w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except OSError:
            pass

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Verification {'PASSED' if ok else 'FAILED'} for {args.trace_id}")
        for c in result["checks"]:
            mark = "PASS" if c.get("ok") else "FAIL"
            print(f"  [{mark}] {c['name']}")
            if not c.get("ok"):
                for k, v in c.items():
                    if k in ("name", "ok"):
                        continue
                    print(f"        {k}: {v}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
