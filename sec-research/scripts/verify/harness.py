"""Stage 4c: Verification harness — two-phase install→trigger driver.

This module provides:
  - _drive_phased: drives ONE PocPlan through the Stage-4a sandbox in two phases
    (install → trigger) and returns a pair of EvidenceCapture records.
  - verify_hypotheses, _persist: orchestrator and persistence (later tasks).

Import resolution for RUNTIME_DIR:
  hooks/ is on sys.path (via tests/conftest.py and the hook federation router).
  ``from lib.paths import RUNTIME_DIR`` resolves because hooks/lib/paths.py
  defines RUNTIME_DIR. This is the same approach used by scripts/llm/generate.py
  (line 17: ``from lib.paths import RUNTIME_DIR``). No local derivation needed.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib.paths import RUNTIME_DIR
from sandbox.runner import SandboxError, sandbox_run
from verify.model import EvidenceCapture
from verify.strategy import PocPlan

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
