"""nightly.py — scheduled nightly entry point.

Pipeline:
    1. Refresh program scopes from venues -> programs/<slug>/        (Stage 2 refresh — STUB; intake is the separate fetch_program.py)
    2. Refresh disclosed-reports cache -> programs/<slug>/disclosed/ (Stage 2 refresh — STUB)
    3. Recon -> runtime/recon/<slug>/                                (Stage 3 — WIRED: recon_program.run_recon)
    4. Hypothesis generation from recon + class playbooks           (Stage 4b — WIRED: llm.generate.generate_hypotheses)
    5. Sandboxed deterministic verification of candidates           (Stage 4c — WIRED: verify.harness.verify_hypotheses, docker)
    6. Triage/dedup -> draft findings -> findings/<trace>/          (Stage 5/6 — WIRED: triage.dedup + draft.drafter)
    7. Append to runtime/briefings/<date>.md                        (always-on)

Stages 3-6 are wired to real modules; the verify stage requires a reachable docker
engine in WSL2 (fail-closed via SandboxError otherwise). Hypothesis generation needs an
LLM provider (Claude API key or local llama-server). Stage-4 was proven live against real
containers on 2026-06-26 via the VERIFY_LIVE=1 gated tests; autonomous novel-finding
discovery against a real loaded program is the remaining work.

Hooks fire normally throughout. Errors on safe side: any hook block ends
the run with structured exit code; the next morning the researcher sees the
failure in the briefing.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.paths import (  # noqa: E402
    PROGRAMS_DIR, RUNTIME_RECON_DIR, RUNTIME_BRIEFINGS_DIR, RUNTIME_SCHEDULED_RUNS,
    FINDINGS_DIR,
)
from lib.scope_match import load_all_scopes  # noqa: E402
from lib import ledger  # noqa: E402
from recon_program import run_recon  # noqa: E402
from llm.generate import generate_hypotheses  # noqa: E402
from verify.harness import verify_hypotheses  # noqa: E402
from verify.model import Verdict, EvidenceCapture  # noqa: E402
from triage.dedup import triage_verdicts  # noqa: E402
from triage.recon_advisories import load_advisories  # noqa: E402
from triage.persist import persist_triage  # noqa: E402
from triage.model import TRIAGE_NOVEL  # noqa: E402
from draft.drafter import draft_findings  # noqa: E402

FINDINGS_ROOT = FINDINGS_DIR


def _verdict_from_dict(vd: dict) -> Verdict:
    """Reconstruct a Verdict dataclass from a serialized dict (as returned by
    verify_hypotheses via asdict()). Rebuilds nested EvidenceCapture objects so
    Stage 6 can access evidence[i].exit_code / .stdout_sha256 via attribute access.

    The 'verified' key (added by the harness for the briefing counter) is stripped
    before reconstruction — it is not a Verdict field.
    """
    evidence = [EvidenceCapture(**e) for e in vd.get("evidence", [])]
    fields = {k: v for k, v in vd.items() if k not in ("verified", "evidence")}
    return Verdict(**fields, evidence=evidence)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def stage_refresh_scopes(scopes: dict) -> list[str]:
    """STUB (Stage 2). For Stage 1, just lists currently-loaded scopes."""
    return [f"scope already loaded: {slug}" for slug in scopes]


def stage_refresh_disclosed(scopes: dict) -> list[str]:
    """STUB (Stage 2)."""
    return [f"disclosed-cache refresh skipped (Stage 2): {slug}" for slug in scopes]


def stage_recon(scopes: dict) -> list[dict]:
    """Stage 3 recon — per-asset known-vulnerability baseline."""
    return run_recon(scopes)


def stage_hypothesize(scopes: dict, recon: list) -> list[dict]:
    """Stage 4b — LLM reads each recon item + class playbooks, emits scope-bounded,
    schema-validated candidate hypotheses. ScopeViolation propagates (audit)."""
    return generate_hypotheses(scopes, recon)


def stage_verify(hypotheses: list) -> list[dict]:
    """Stage 4c — build a per-hypothesis PoC, run it phased through the Stage-4a
    sandbox (install -> trigger/--network none), and emit verified/refuted/skipped/
    error verdicts. ScopeViolation propagates (audit); SandboxError/SeedIncomplete
    are isolated per item. Each returned dict carries a 'verified' bool for the
    briefing counter."""
    return verify_hypotheses(hypotheses)


def stage_triage(verdicts: list, slug: str, *, now: str) -> list:
    """Stage 5 — dedup verified verdicts vs recon's pre-fetched advisories.

    Returns the novel verdicts (no known-CVE match) for drafting; duplicates are
    persisted and dropped.

    Args:
        verdicts: List of Verdict dataclasses to triage (typically VERDICT_VERIFIED).
        slug: Program slug used to load the matching recon advisories.
        now: ISO-8601 UTC timestamp string; use nightly's _utc_now_iso() at call site.

    Returns:
        List of Verdict instances whose triage_status is TRIAGE_NOVEL.
    """
    advisories = load_advisories(slug)
    results = triage_verdicts(verdicts, advisories, now=now)
    persist_triage(slug, results)
    return [r.verdict for r in results if r.triage_status == TRIAGE_NOVEL]


def stage_draft_findings(novel: list, slug: str, *, today: str) -> list[str]:
    """Stage 6 — deterministically draft schema-valid findings for novel verdicts.

    Args:
        novel: Novel Verdict instances from stage_triage for this slug.
        slug: Program slug — used to load the slug's own advisories for template rendering.
        today: ISO date YYYY-MM-DD (from _today()) for trace_id allocation.

    Returns:
        List of trace_ids for successfully drafted findings.
    """
    advisories = load_advisories(slug)
    results = draft_findings(novel, advisories, findings_root=FINDINGS_ROOT, today=today)
    return [r.trace_id for r in results]


def stage_briefing(scopes: dict, recon: list, hypotheses: list, verified: list, drafts: list) -> Path:
    """Always-on. Writes runtime/briefings/<date>.md with summary."""
    today = _today()
    briefing_path = RUNTIME_BRIEFINGS_DIR / f"{today}.md"
    RUNTIME_BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    body = f"""# Morning Briefing — {today}

Generated: {_utc_now_iso()}
Pipeline: Stages 3-6 wired; sandbox+verify harness proven live on real Docker (2026-06-26)

## Loaded program scopes ({len(scopes)})
"""
    for slug, scope in scopes.items():
        body += f"- `{slug}` ({scope.get('venue', '?')}): "
        body += f"{len(scope.get('in_scope', []))} in-scope, "
        body += f"{len(scope.get('out_of_scope', []))} out-of-scope\n"

    body += f"""
## Pipeline summary
- Recon items: {len(recon)}
- Hypotheses generated: {len(hypotheses)}
- Verified candidates: {sum(1 for v in verified if v.get('verified'))}
- Findings drafted: {len(drafts)} (trace-ids: {', '.join(drafts) if drafts else 'none'})

## Action items
- A run produces findings only when a program scope is loaded AND hypotheses verify novel
  (known-CVE verdicts dedup to true-negatives by design).
- Next: autonomous discovery of a novel finding against a real loaded program.

## Ledger health
- Total entries: {len(ledger.read_all())}
- Recent: see `submissions/ledger.jsonl`
"""

    briefing_path.write_text(body, encoding="utf-8")
    return briefing_path


def main() -> int:
    started_at = _utc_now_iso()
    print(f"=== nightly.py started at {started_at} ===")

    scopes = load_all_scopes()
    print(f"Loaded {len(scopes)} program scope(s)")

    refresh_log = stage_refresh_scopes(scopes)
    disclosed_log = stage_refresh_disclosed(scopes)
    recon = stage_recon(scopes)
    hypotheses = stage_hypothesize(scopes, recon)
    verified = stage_verify(hypotheses)

    # Stage 5 + 6: triage then draft — group verified Verdict objects by slug,
    # dedup against recon advisories (Stage 5), draft novel findings per slug (Stage 6).
    now_ts = _utc_now_iso()
    today = _today()
    all_drafts: list[str] = []
    by_slug: dict[str, list] = {}
    for vd in verified:
        slug_key = vd.get("program_slug", "")
        if not slug_key:
            print(f"[nightly] warning: verdict missing program_slug, bucketing under '': {vd.get('hypothesis_id', '?')}")
        by_slug.setdefault(slug_key, []).append(vd)
    for slug_key, vd_list in by_slug.items():
        verdicts_typed = [_verdict_from_dict(vd) for vd in vd_list]
        novel = stage_triage(verdicts_typed, slug_key, now=now_ts)
        all_drafts.extend(stage_draft_findings(novel, slug_key, today=today))

    drafts = all_drafts
    briefing = stage_briefing(scopes, recon, hypotheses, verified, drafts)

    finished_at = _utc_now_iso()
    print(f"Briefing written: {briefing}")
    print(f"=== nightly.py finished at {finished_at} ===")

    # Log run
    RUNTIME_SCHEDULED_RUNS.parent.mkdir(parents=True, exist_ok=True)
    with RUNTIME_SCHEDULED_RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "kind": "nightly",
            "started_at": started_at,
            "finished_at": finished_at,
            "scopes_loaded": len(scopes),
            "drafts_produced": len(drafts),
            "briefing_path": str(briefing),
        }) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
