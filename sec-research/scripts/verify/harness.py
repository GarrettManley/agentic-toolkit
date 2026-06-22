"""Stage 4c: Verification harness — two-phase install→trigger driver.

This module provides:
  - _drive_phased: drives ONE PocPlan through the Stage-4a sandbox in two phases
    (install → trigger) and returns a pair of EvidenceCapture records.
  - verify_hypotheses: batch orchestrator that turns hypotheses into verdict dicts.
  - _persist: persistence helper (Task 6).

Import resolution for RUNTIME_DIR:
  hooks/ is on sys.path (via tests/conftest.py and the hook federation router).
  ``from lib.paths import RUNTIME_DIR`` resolves because hooks/lib/paths.py
  defines RUNTIME_DIR. This is the same approach used by scripts/llm/generate.py
  (line 17: ``from lib.paths import RUNTIME_DIR``). No local derivation needed.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from lib import ledger
from lib.paths import RUNTIME_DIR
from sandbox.runner import SandboxError, sandbox_run
from verify.model import (
    VERDICT_ERROR,
    VERDICT_REFUTED,
    VERDICT_SKIPPED,
    VERDICT_VERIFIED,
    EvidenceCapture,
    Verdict,
    derive_verdict,
)
from verify.strategy import PocPlan, PocStrategy, SeedIncomplete

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

RUNTIME_VERDICTS_DIR = RUNTIME_DIR / "verdicts"

# Named timeout constants — no magic numbers in call sites.
INSTALL_TIMEOUT_S: int = 180
"""Wall-clock timeout in seconds for the install sandbox phase."""

TRIGGER_TIMEOUT_S: int = 120
"""Wall-clock timeout in seconds for the trigger sandbox phase."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    """Return an ISO-8601 UTC string (no sub-second, Z suffix). Matches generate.py."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _reason_for(vstr: str, trigger_ev: EvidenceCapture, plan: PocPlan) -> str:
    """Return a short human-readable reason string for a verdict.

    Args:
        vstr: One of VERDICT_VERIFIED, VERDICT_REFUTED, VERDICT_ERROR.
        trigger_ev: The EvidenceCapture from the trigger phase.
        plan: The PocPlan whose expected values define the success condition.

    Returns:
        A human-readable string appropriate for Verdict.reason.
    """
    if vstr == VERDICT_VERIFIED:
        return f"exploit reproduced (exit {trigger_ev.exit_code}, stdout hash matched)"
    if vstr == VERDICT_REFUTED:
        sha_status = (
            "matched"
            if trigger_ev.stdout_sha256 == plan.expected_trigger_sha256
            else "mismatch"
        )
        return (
            f"not reproduced: exit {trigger_ev.exit_code} "
            f"(expected {plan.expected_trigger_exit}), stdout hash {sha_status}"
        )
    # VERDICT_ERROR — the only derive_verdict error path is timed_out
    return "trigger timed out"


# ---------------------------------------------------------------------------
# _drive_phased — two-phase install→trigger driver
# ---------------------------------------------------------------------------

def _drive_phased(
    plan: PocPlan,
    hypothesis_id: str,
    slug: str,
    *,
    runner=subprocess.run,
    verdict_root: Path | None = None,
) -> tuple[EvidenceCapture, EvidenceCapture]:
    """Drive one PocPlan through two sandbox phases and return evidence.

    Phase 1 — install (``phase="install"``, ``--network bridge``):
      Materializes plan.files into a per-hypothesis workdir, then installs the
      vulnerable package via sandbox_run with network_allow=plan.install_hosts.
      check_http gates each declared host before the container starts.

    Phase 2 — trigger (``phase="execute"``, ``--network none``):
      Runs plan.trigger_cmd in the same workdir, airgapped per C2. The install
      phase writes node_modules/; the trigger reads it — shared workdir is the
      handoff channel.

    Args:
        plan: The PocPlan to execute.
        hypothesis_id: Unique identifier for the hypothesis under test.
        slug: Program slug, used to namespace the workdir under verdict_root.
        runner: Injectable subprocess.run replacement for offline tests.
        verdict_root: Override root for the workdir tree (default: RUNTIME_VERDICTS_DIR).

    Returns:
        (install_ev, trigger_ev) — a pair of EvidenceCapture records.
        install_ev.phase == "install"; trigger_ev.phase == "trigger".

    Raises:
        SandboxError: If the install phase exits non-zero or times out.
            The trigger phase is NEVER attempted after an install failure.
        SandboxError: Propagated from sandbox_run if docker is unreachable.
        ScopeViolation: Propagated uncaught from sandbox_run's install-phase
            check_http call. The caller (verify_hypotheses) must not catch it
            so the batch aborts (C1).

    Note:
        _drive_phased does NOT compute a verdict and does NOT catch SandboxError
        or ScopeViolation. Both exception types propagate to the caller.
    """
    root = verdict_root or RUNTIME_VERDICTS_DIR
    W: Path = root / slug / "work" / hypothesis_id
    W.mkdir(parents=True, exist_ok=True)

    # Materialize plan files into the workdir before install.
    for name, content in plan.files.items():
        (W / name).write_text(content, encoding="utf-8")

    # -----------------------------------------------------------------------
    # Phase 1: install
    # -----------------------------------------------------------------------
    install_res = sandbox_run(
        plan.install_cmd,
        ecosystem=plan.ecosystem,
        phase="install",
        workdir_host=W,
        timeout=INSTALL_TIMEOUT_S,
        network_allow=plan.install_hosts,
        runner=runner,
    )
    install_ev = EvidenceCapture(
        phase="install",
        exit_code=install_res.exit_code,
        stdout_sha256=install_res.stdout_sha256,
        timed_out=install_res.timed_out,
        duration_s=install_res.duration_s,
    )

    # Short-circuit: trigger must NOT run if install failed or timed out.
    if install_res.timed_out or install_res.exit_code != 0:
        raise SandboxError(
            f"install phase failed: exit={install_res.exit_code} "
            f"timed_out={install_res.timed_out}"
        )

    # -----------------------------------------------------------------------
    # Phase 2: trigger (--network none, per C2)
    # -----------------------------------------------------------------------
    trigger_res = sandbox_run(
        plan.trigger_cmd,
        ecosystem=plan.ecosystem,
        phase="execute",
        workdir_host=W,
        timeout=TRIGGER_TIMEOUT_S,
        runner=runner,
    )
    trigger_ev = EvidenceCapture(
        phase="trigger",
        exit_code=trigger_res.exit_code,
        stdout_sha256=trigger_res.stdout_sha256,
        timed_out=trigger_res.timed_out,
        duration_s=trigger_res.duration_s,
    )

    return install_ev, trigger_ev


# ---------------------------------------------------------------------------
# verify_hypotheses — batch orchestrator
# ---------------------------------------------------------------------------

def verify_hypotheses(
    hypotheses: list[dict],
    *,
    strategy: PocStrategy | None = None,
    runner=subprocess.run,
    verdict_root: Path | None = None,
    now: datetime | None = None,
) -> list[dict]:
    """Turn a batch of hypotheses into verdict dicts.

    For each hypothesis: select strategy, validate seed, drive the phased PoC
    via _drive_phased, derive the verdict, isolate per-item failures, emit
    ledger events, and persist verdicts grouped by slug via _persist.

    Args:
        hypotheses: List of hypothesis dicts as produced by Stage 4b.
        strategy: PocStrategy to use; defaults to select_strategy() if None.
        runner: Injectable subprocess.run replacement for offline tests.
        verdict_root: Override root for workdir trees; default RUNTIME_VERDICTS_DIR.
        now: Override UTC datetime for timestamps; default datetime.now(UTC).

    Returns:
        List of verdict dicts (dataclasses.asdict(Verdict) | {"verified": bool}).
        Order matches the input hypotheses list.

    Raises:
        ScopeViolation: Propagated uncaught from _drive_phased (constraint C1).
            Only SeedIncomplete and SandboxError are caught per-item.
    """
    from verify.strategy import select_strategy  # lazy — avoids circular import risk

    strategy = strategy or select_strategy()
    now = now or datetime.now(timezone.utc)
    verdicts: list[Verdict] = []

    ledger.append_event("verify-started", count=len(hypotheses))

    for h in hypotheses:
        hid = h["hypothesis_id"]
        slug = h.get("program_slug", "")
        _t = h.get("target", {})
        _ident = _t.get("identifier", "")
        _ver = _t.get("version_or_revision")
        tid = f"{_ident}@{_ver}" if _ver else _ident
        vcls = h.get("vuln_class", "")

        def _mk(verdict: str, reason: str, evidence: list, template_id) -> Verdict:
            return Verdict(hid, slug, tid, vcls, verdict, reason, strategy.name, template_id, evidence, _iso(now))

        if not strategy.supports(h):
            ledger.append_event("verify-no-strategy", slug=slug, hypothesis_id=hid)
            verdicts.append(_mk(VERDICT_SKIPPED, "no matching PoC strategy", [], None))
            continue

        try:
            plan = strategy.build_plan(h)
        except SeedIncomplete as e:
            ledger.append_event(
                "verify-seed-incomplete", slug=slug, hypothesis_id=hid, missing=e.missing
            )
            verdicts.append(
                _mk(VERDICT_SKIPPED, f"evidence_seed incomplete: {e.missing}", [], None)
            )
            continue

        # ScopeViolation from _drive_phased MUST propagate uncaught (constraint C1).
        # Do NOT add except Exception or except ScopeViolation here.
        try:
            install_ev, trigger_ev = _drive_phased(
                plan, hid, slug, runner=runner, verdict_root=verdict_root
            )
        except SandboxError as e:
            ledger.append_event(
                "verify-sandbox-error", slug=slug, hypothesis_id=hid, error=str(e)
            )
            verdicts.append(
                _mk(VERDICT_ERROR, f"sandbox error: {e}", [], plan.template_id)
            )
            continue

        vstr = derive_verdict(trigger_ev, plan)
        reason = _reason_for(vstr, trigger_ev, plan)
        ledger.append_event(
            "verify-verdict",
            slug=slug,
            hypothesis_id=hid,
            verdict=vstr,
            template_id=plan.template_id,
        )
        verdicts.append(_mk(vstr, reason, [install_ev, trigger_ev], plan.template_id))

    _persist(verdicts, verdict_root=verdict_root)
    return [asdict(v) | {"verified": v.verdict == VERDICT_VERIFIED} for v in verdicts]


# ---------------------------------------------------------------------------
# _persist — write verdicts grouped by slug to runtime/verdicts/<slug>/verdicts.json
# ---------------------------------------------------------------------------

def _persist(verdicts: list[Verdict], *, verdict_root: Path | None = None) -> None:
    """Persist verdicts to disk, grouped by program slug.

    Mirrors scripts/llm/generate.py's ``_persist`` (group-by-slug, one JSON file
    per slug). Best-effort: an ``OSError`` during a write is caught, a
    ``verify-persist-error`` ledger event is emitted for the affected slug, and
    processing continues. An empty ``verdicts`` list is a no-op.

    Args:
        verdicts: List of Verdict dataclasses to persist.
        verdict_root: Override root directory; defaults to RUNTIME_VERDICTS_DIR.

    Writes:
        ``<verdict_root>/<slug>/verdicts.json`` — JSON array of ``asdict(Verdict)``
        records (no ``"verified"`` key; that's only in the return projection from
        ``verify_hypotheses``).
    """
    if not verdicts:
        return

    root = verdict_root or RUNTIME_VERDICTS_DIR

    by_slug: dict[str, list[Verdict]] = {}
    for v in verdicts:
        by_slug.setdefault(v.program_slug, []).append(v)

    for slug, items in by_slug.items():
        prog_dir = root / slug
        try:
            prog_dir.mkdir(parents=True, exist_ok=True)
            (prog_dir / "verdicts.json").write_text(
                json.dumps([asdict(v) for v in items], indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            ledger.append_event("verify-persist-error", slug=slug, error=str(exc))
