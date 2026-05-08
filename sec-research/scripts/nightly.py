"""nightly.py — scheduled nightly entry point (Stage 1 SKELETON).

Pipeline framework:
    1. Refresh program scopes from venues -> programs/<slug>/        (Stage 2 — STUB)
    2. Refresh disclosed-reports cache -> programs/<slug>/disclosed/ (Stage 2 — STUB)
    3. Recon -> runtime/recon/<slug>/                                (Stage 3 — STUB)
    4. Hypothesis generation via fast_orchestrator.py + playbooks    (Stage 4 — STUB)
    5. Sandboxed verification of candidates                          (Stage 4 — STUB)
    6. Draft findings -> findings/<trace>/                           (Stage 6 — STUB)
    7. Append to runtime/briefings/<date>.md

In Stage 1, stages 1-6 are NO-OPs. Stage 7 still runs to produce a briefing
proving the pipeline framework + hooks + ledger work end-to-end on fixture data.

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

from lib.paths import (  # noqa: E402
    PROGRAMS_DIR, RUNTIME_RECON_DIR, RUNTIME_BRIEFINGS_DIR, RUNTIME_SCHEDULED_RUNS,
    FINDINGS_DIR,
)
from lib.scope_match import load_all_scopes  # noqa: E402
from lib import ledger  # noqa: E402


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
    """STUB (Stage 3). Returns empty recon for Stage 1."""
    return []


def stage_hypothesize(scopes: dict, recon: list) -> list[dict]:
    """STUB (Stage 4). No hypotheses for Stage 1."""
    return []


def stage_verify(hypotheses: list) -> list[dict]:
    """STUB (Stage 4). Trivially returns input as 'unverified'."""
    return [{"hypothesis": h, "verified": False, "reason": "Stage 1 stub"} for h in hypotheses]


def stage_draft_findings(verified: list) -> list[str]:
    """STUB (Stage 6). Returns empty — no automated drafting in Stage 1."""
    return []


def stage_briefing(scopes: dict, recon: list, hypotheses: list, verified: list, drafts: list) -> Path:
    """Always-on. Writes runtime/briefings/<date>.md with summary."""
    today = _today()
    briefing_path = RUNTIME_BRIEFINGS_DIR / f"{today}.md"
    RUNTIME_BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    body = f"""# Morning Briefing — {today}

Generated: {_utc_now_iso()}
Stage: 1 (foundation) — skeletons only; pipeline body is fixture-data

## Loaded program scopes ({len(scopes)})
"""
    for slug, scope in scopes.items():
        body += f"- `{slug}` ({scope.get('venue', '?')}): "
        body += f"{len(scope.get('in_scope', []))} in-scope, "
        body += f"{len(scope.get('out_of_scope', []))} out-of-scope\n"

    body += f"""
## Pipeline summary
- Recon items: {len(recon)} (Stage 3 stub)
- Hypotheses generated: {len(hypotheses)} (Stage 4 stub)
- Verified candidates: {sum(1 for v in verified if v.get('verified'))} (Stage 4 stub)
- Drafts produced: {len(drafts)} (Stage 6 stub)

## Action items
- Stage 1 is foundation only; no real findings expected from skeleton runs.
- To advance: implement Stage 2 (program intake) — see `docs/CHARTER.md` § Roadmap.

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
    drafts = stage_draft_findings(verified)
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
