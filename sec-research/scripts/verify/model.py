"""Stage 4c: Verdict model — EvidenceCapture, Verdict frozen dataclasses,
VERDICT_* string constants, and the pure derive_verdict() helper.

Import direction: model.py imports PocPlan from strategy.py. strategy.py does NOT
import from model.py. This one-way dependency avoids any circular import.
"""
from __future__ import annotations

from dataclasses import dataclass

from verify.strategy import PocPlan


# ---------------------------------------------------------------------------
# Verdict string constants
# ---------------------------------------------------------------------------

VERDICT_VERIFIED = "verified"
"""PoC actually triggered observable vulnerable behavior: exit_code and
stdout_sha256 both matched the plan's expected values."""

VERDICT_REFUTED = "refuted"
"""PoC ran to completion but the trigger output did not match expectations.
The vulnerability may have been patched or the template assumptions are wrong."""

VERDICT_SKIPPED = "skipped"
"""Hypothesis could not be tested — either no strategy supports it or required
evidence_seed fields were missing. Distinct from refuted: no sandbox run occurred."""

VERDICT_ERROR = "error"
"""Execution failure: the sandbox was unreachable, the install phase failed, or
the trigger timed out. Verdict is indeterminate."""


# ---------------------------------------------------------------------------
# EvidenceCapture — one phase's captured execution result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceCapture:
    """Immutable snapshot of a single sandbox phase execution result.

    Two EvidenceCaptures are collected per hypothesis: one for the install phase
    and one for the trigger phase. The trigger EvidenceCapture is the input to
    derive_verdict().
    """

    phase: str
    """Phase identifier: "install" or "trigger"."""

    exit_code: int
    """Process exit code from the sandbox container."""

    stdout_sha256: str
    """sha256 hex digest of the captured stdout. Used for deterministic verdict
    comparison against plan.expected_trigger_sha256."""

    timed_out: bool
    """True if the sandbox container hit its timeout ceiling before exiting."""

    duration_s: float
    """Wall-clock execution time in seconds, as measured by the runner."""


# ---------------------------------------------------------------------------
# Verdict — the final per-hypothesis verdict record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Verdict:
    """Immutable record of the outcome of verifying one hypothesis.

    Persisted to runtime/verdicts/<slug>/verdicts.json by harness._persist().
    Stage 6 (finding-drafting) reads only VERDICT_VERIFIED records.
    """

    hypothesis_id: str
    """Matches hypothesis["hypothesis_id"] from the input feed."""

    program_slug: str
    """Program slug, e.g. "huntr-npm-minimatch"."""

    target_identifier: str
    """Human-readable target, e.g. "minimatch@3.0.4"."""

    vuln_class: str
    """Vulnerability class from the hypothesis, e.g. "dependency-cve"."""

    verdict: str
    """One of VERDICT_VERIFIED, VERDICT_REFUTED, VERDICT_SKIPPED, VERDICT_ERROR."""

    reason: str
    """Human-readable explanation — actual-vs-expected for refuted, error message
    for error, "exit+sha match" for verified, "no-strategy" for skipped."""

    strategy: str
    """Strategy name that produced the plan, e.g. "templated"."""

    template_id: str | None
    """Template ID from the plan, or None if no plan was built (skipped/error)."""

    evidence: list[EvidenceCapture]
    """Zero, one, or two EvidenceCapture records (install + trigger phases).
    Empty for skipped verdicts; may contain only install for early-error verdicts."""

    verified_at: str
    """ISO-8601 UTC timestamp, e.g. "2026-06-22T00:00:00Z"."""


# ---------------------------------------------------------------------------
# derive_verdict — pure function, no sandbox
# ---------------------------------------------------------------------------

def derive_verdict(trigger: EvidenceCapture, plan: PocPlan) -> str:
    """Derive a verdict string from the trigger phase result and the plan's expectations.

    Pure function — no sandbox calls, no I/O, no side effects.

    Priority:
    1. timed_out=True → VERDICT_ERROR (execution was indeterminate).
    2. exit_code matches AND stdout_sha256 matches → VERDICT_VERIFIED.
    3. Any other combination → VERDICT_REFUTED.

    Args:
        trigger: The EvidenceCapture from the trigger (execute) phase.
        plan: The PocPlan whose expected_trigger_exit and expected_trigger_sha256
              define the success condition.

    Returns:
        One of VERDICT_VERIFIED, VERDICT_REFUTED, or VERDICT_ERROR.
        Never returns VERDICT_SKIPPED — skipped verdicts are set by the harness
        before a plan is built.
    """
    if trigger.timed_out:
        return VERDICT_ERROR

    if (
        trigger.exit_code == plan.expected_trigger_exit
        and trigger.stdout_sha256 == plan.expected_trigger_sha256
    ):
        return VERDICT_VERIFIED

    return VERDICT_REFUTED


# ---------------------------------------------------------------------------
# derive_differential_verdict — the trust oracle
# ---------------------------------------------------------------------------


def _matches(ev: EvidenceCapture, exit_code: int, sha: str) -> bool:
    return ev.exit_code == exit_code and ev.stdout_sha256 == sha


def derive_differential_verdict(
    affected: EvidenceCapture, fixed: EvidenceCapture, plan: PocPlan
) -> tuple[str, str]:
    """Differential trust oracle. Pure function — no I/O.

    The SAME authored PoC is run against the affected and fixed versions. A real
    exploit fires on the affected version (verified signature) and is silenced on
    the fixed version (refuted signature). Any other shape is untrusted.

    Returns (verdict, reason_code). Never laundered: output matching neither the
    verified nor the refuted signature is ERROR, not REFUTED (hb-be9).
    """
    if affected.timed_out or fixed.timed_out:
        return VERDICT_ERROR, "timeout"

    aff_confirmed = _matches(affected, plan.expected_trigger_exit, plan.expected_trigger_sha256)
    aff_patched = _matches(affected, plan.expected_refuted_exit, plan.expected_refuted_sha256)
    fix_confirmed = _matches(fixed, plan.expected_trigger_exit, plan.expected_trigger_sha256)
    fix_patched = _matches(fixed, plan.expected_refuted_exit, plan.expected_refuted_sha256)

    if aff_confirmed:
        if fix_patched:
            return VERDICT_VERIFIED, "discriminates"
        if fix_confirmed:
            return VERDICT_ERROR, "no-discrimination"
        return VERDICT_ERROR, "fixed-indeterminate"
    if aff_patched:
        return VERDICT_REFUTED, "affected-not-vulnerable"
    return VERDICT_ERROR, "affected-indeterminate"
