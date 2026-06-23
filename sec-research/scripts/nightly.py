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

    # Stage 5: triage — group verified Verdict objects by slug, dedup against
    # recon advisories, collect novel verdicts across all programs.
    now_ts = _utc_now_iso()
    novel: list = []
    by_slug: dict[str, list] = {}
    for vd in verified:
        slug_key = vd.get("program_slug", "")
        if not slug_key:
            print(f"[nightly] warning: verdict missing program_slug, bucketing under '': {vd.get('hypothesis_id', '?')}")
        by_slug.setdefault(slug_key, []).append(vd)
    for slug_key, vd_list in by_slug.items():
        verdicts_typed = [_verdict_from_dict(vd) for vd in vd_list]
        novel.extend(stage_triage(verdicts_typed, slug_key, now=now_ts))

    drafts = stage_draft_findings(novel)
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
