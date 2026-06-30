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

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
# Workspace root, so absolute `scripts.verify.model`-style imports used by some stage
# modules (e.g. triage/dedup.py) resolve when run as a script — not just under pytest,
# which already puts the root on the path. Both `verify.*` and `scripts.verify.*` then
# resolve as namespace packages, mirroring the test environment.
WORKSPACE_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from lib.paths import (  # noqa: E402
    PROGRAMS_DIR, RUNTIME_RECON_DIR, RUNTIME_BRIEFINGS_DIR, RUNTIME_SCHEDULED_RUNS,
    FINDINGS_DIR,
)
from lib.scope_match import load_all_scopes  # noqa: E402
from lib import ledger  # noqa: E402
from lib.journal import RunJournal  # noqa: E402
from recon_program import run_recon  # noqa: E402
from llm.generate import generate_hypotheses  # noqa: E402
from llm.client import select_client  # noqa: E402
from sandbox.doctor import sandbox_doctor  # noqa: E402
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


HYPOTHESIZE_FAILURE_EVENTS = {"hypothesis-llm-unavailable", "hypothesis-parse-error"}


def _hypothesize_failures_since(before_count: int) -> list[dict]:
    """Ledger entries appended since `before_count` whose event_type is a transient/infra
    hypothesize-stage failure (LLM unreachable or its response unparseable) -- NOT a reasoned
    drop (out-of-scope/invalid/target-divergence/version-unresolved), which stays silent by
    design.

    A 'clean' zero-hypotheses outcome is only defensible if every per-item drop was a reasoned
    decision; a transient failure produces the exact same terminal shape. hb-322's first live
    run discovered this masking pattern for real (see
    docs/superpowers/research/2026-06-30-hb-322-first-real-run.md) -- this is the generalized
    fix for the swallow-and-continue architecture in generate_hypotheses, covering both the
    unattended cron path and the supervised path's live checkpoint.
    """
    return [e for e in ledger.read_all()[before_count:]
            if e.get("event_type") in HYPOTHESIZE_FAILURE_EVENTS]


def _failure_identifier(event: dict) -> str:
    """Best available per-recon-item identifier for a hypothesize-stage failure event.

    `slug` on these events is the program-level scope slug (set once per program; see
    scripts/recon/recon_item.py), constant across every recon item/asset in the run -- NOT a
    per-item identifier. `asset` (captured for hypothesis-llm-unavailable, see generate.py)
    names the actual failing recon item and must be preferred when present; fall back to
    `slug` only for event types that don't capture it (hypothesis-parse-error).
    """
    return event.get("asset") or event["slug"]


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


def stage_briefing(scopes: dict, recon: list, hypotheses: list, verified: list, drafts: list,
                   *, ledger_count_before_run: int = 0) -> Path:
    """Always-on. Writes runtime/briefings/<date>.md with summary.

    ``ledger_count_before_run`` (a ledger.read_all() length snapshot taken before stage_recon)
    surfaces hb-a2w's hypothesize-stage transient-failure detection for BOTH entry points --
    run_unattended (cron, no journal at all -- this briefing is the only artifact a human is
    guaranteed to read) and run_supervised (which also gets a live stderr/journal warning at
    its hypothesize checkpoint; see the Stage 4b block in run_supervised).
    """
    today = _today()
    briefing_path = RUNTIME_BRIEFINGS_DIR / f"{today}.md"
    RUNTIME_BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    hyp_failures = _hypothesize_failures_since(ledger_count_before_run)

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
"""

    if hyp_failures:
        failure_desc = ", ".join(
            f"{e.get('event_type')}@{_failure_identifier(e)} ({e['entry_id']})"
            for e in hyp_failures
        )
        body += f"""
## Hypothesize-stage failures ({len(hyp_failures)})
This run logged {len(hyp_failures)} transient LLM failure(s) during hypothesis generation
(LLM-unavailable or unparseable response) -- NOT reasoned zero-hypotheses drops. Any null
result above may be partly or wholly a masked failure rather than a genuine reasoned
decision: {failure_desc}
"""

    body += f"""
## Ledger health
- Total entries: {len(ledger.read_all())}
- Recent: see `submissions/ledger.jsonl`
"""

    briefing_path.write_text(body, encoding="utf-8")
    return briefing_path


def run_unattended() -> int:
    """Default nightly path: run the whole pipeline end-to-end with no halts (cron)."""
    started_at = _utc_now_iso()
    print(f"=== nightly.py started at {started_at} ===")

    scopes = load_all_scopes()
    print(f"Loaded {len(scopes)} program scope(s)")
    ledger_count_before_run = len(ledger.read_all())

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
    briefing = stage_briefing(scopes, recon, hypotheses, verified, drafts,
                              ledger_count_before_run=ledger_count_before_run)

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


# --------------------------------------------------------------------------- #
# Supervised driver (hb-322): same pipeline, stage-gated with inspection halts  #
# and an incremental run journal. Reuses the stage_* functions above verbatim —  #
# no new pipeline logic.                                                         #
# --------------------------------------------------------------------------- #

SUPERVISED_STAGES = ["recon", "hypothesize", "verify", "triage", "draft"]


def _preflight(*, provider: str | None = None) -> list[str]:
    """Fail-loud readiness check before a supervised run. Confirms the LLM provider is
    configured/reachable (token-free) and the docker sandbox is up, so a misconfigured
    provider aborts loudly instead of silently yielding zero hypotheses (a false null).

    Raises LLMConfigError / LLMUnavailable (provider) or RuntimeError (sandbox)."""
    select_client(provider).preflight()
    ok, msgs = sandbox_doctor()
    if not ok:
        raise RuntimeError("sandbox preflight failed: " + "; ".join(msgs))
    return msgs


def _pause_for_inspection(stage: str, summary: str) -> bool:
    """Print a checkpoint summary and block for an operator decision. Returns True to
    continue, False to abort. Overridable in tests; EOF (non-interactive) aborts safely."""
    print(f"\n--- CHECKPOINT: {stage} ---\n{summary}")
    try:
        resp = input(f"Continue past {stage}? [y/N] ").strip().lower()
    except EOFError:
        return False
    return resp in ("y", "yes")


def run_supervised(*, until: str | None = None, auto_yes: bool = False,
                   provider: str | None = None, journals_dir: Path | None = None) -> int:
    """Drive the pipeline one stage at a time, halting for inspection between stages and
    recording each checkpoint to a run journal. ``until`` stops after the named stage;
    ``auto_yes`` skips the interactive halts (still journals)."""
    started_at = _utc_now_iso()
    today = _today()
    print(f"=== nightly.py --supervised started at {started_at} ===")

    # Bridge --provider to the env var that every stage's select_client() reads — the
    # stage functions (hypothesis, and the verify stage's LLM PoC authoring) each resolve
    # their own client from SECRESEARCH_LLM_PROVIDER, so a bare param wouldn't reach them.
    if provider:
        os.environ["SECRESEARCH_LLM_PROVIDER"] = provider

    _preflight(provider=provider)  # aborts loudly on misconfig

    scopes = load_all_scopes()
    if not scopes:
        print("No program scopes loaded. Load one first, e.g.:\n"
              "  python scripts/fetch_program.py --venue huntr --identifier <owner>/<pkg>",
              file=sys.stderr)
        return 2

    slug = next(iter(scopes))
    journal = RunJournal(slug, date=today, journals_dir=journals_dir)
    journal.start(program_reason=f"Supervised run over loaded scope(s): {', '.join(scopes)}")

    def _halt(stage: str, summary: str) -> bool:
        journal.checkpoint(stage, outcome="reached", detail=summary)
        return True if auto_yes else _pause_for_inspection(stage, summary)

    def _stop(reason: str) -> int:
        journal.finish(outcome=reason)
        print(f"Journal: {journal.path}")
        return 0

    # Stage 3 — recon
    ledger_count_before_run = len(ledger.read_all())
    recon = stage_recon(scopes)
    if not _halt("recon", f"recon items: {len(recon)} -> {RUNTIME_RECON_DIR}"):
        return _stop("aborted at recon")
    if until == "recon":
        return _stop("stopped after recon (--until)")

    # Stage 4b — hypothesis
    hypotheses = stage_hypothesize(scopes, recon)
    if not _halt("hypothesize", f"hypotheses generated: {len(hypotheses)}"):
        return _stop("aborted at hypothesize")
    if until == "hypothesize":
        return _stop("stopped after hypothesize (--until)")

    # Stage 4c — verify
    verified = stage_verify(hypotheses)
    n_ok = sum(1 for v in verified if v.get("verified"))
    if not _halt("verify", f"verdicts: {len(verified)} ({n_ok} verified)"):
        return _stop("aborted at verify")
    if until == "verify":
        return _stop("stopped after verify (--until)")

    # Stage 5 — triage (collect novel per slug; no drafting yet)
    now_ts = _utc_now_iso()
    by_slug: dict[str, list] = {}
    for vd in verified:
        by_slug.setdefault(vd.get("program_slug", ""), []).append(vd)
    novel_by_slug = {
        slug_key: stage_triage([_verdict_from_dict(vd) for vd in vd_list], slug_key, now=now_ts)
        for slug_key, vd_list in by_slug.items()
    }
    novel_total = sum(len(v) for v in novel_by_slug.values())
    if not _halt("triage", f"novel after dedup: {novel_total}"):
        return _stop("aborted at triage")
    if until == "triage":
        return _stop("stopped after triage (--until)")

    # Stage 6 — draft
    all_drafts: list[str] = []
    for slug_key, novel in novel_by_slug.items():
        all_drafts.extend(stage_draft_findings(novel, slug_key, today=today))
    _halt("draft", f"findings drafted: {len(all_drafts)} ({', '.join(all_drafts) or 'none'})")

    briefing = stage_briefing(scopes, recon, hypotheses, verified, all_drafts,
                              ledger_count_before_run=ledger_count_before_run)
    outcome = (f"DRAFT path — {len(all_drafts)} finding(s): {', '.join(all_drafts)}"
               if all_drafts
               else "NULL result — no novel confirmed finding; see verdicts for the audit trail")
    journal.finish(outcome=outcome)
    print(f"Briefing: {briefing}\nJournal: {journal.path}\nOutcome: {outcome}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="sec-research pipeline driver (unattended nightly, or supervised run)")
    parser.add_argument("--supervised", action="store_true",
                        help="run stage-by-stage with inspection halts and a run journal")
    parser.add_argument("--until", choices=SUPERVISED_STAGES, default=None,
                        help="(supervised) stop after this stage; e.g. --until recon for a dry run")
    parser.add_argument("--yes", action="store_true",
                        help="(supervised) skip interactive halts; still writes the journal")
    parser.add_argument("--provider", default=None,
                        help="LLM provider override (claude|llama); default from env")
    args = parser.parse_args(argv)

    if (args.until or args.yes or args.provider) and not args.supervised:
        parser.error("--until/--yes/--provider require --supervised")
    if args.supervised:
        return run_supervised(until=args.until, auto_yes=args.yes, provider=args.provider)
    return run_unattended()


if __name__ == "__main__":
    sys.exit(main())
