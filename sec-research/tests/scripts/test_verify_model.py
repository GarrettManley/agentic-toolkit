"""Tests for scripts/verify/model.py — EvidenceCapture, Verdict, derive_verdict."""
from __future__ import annotations

import pytest

from verify.model import (
    VERDICT_ERROR,
    VERDICT_REFUTED,
    VERDICT_SKIPPED,
    VERDICT_VERIFIED,
    EvidenceCapture,
    Verdict,
    derive_verdict,
)
from verify.strategy import PocPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plan(
    expected_exit: int = 0,
    expected_sha: str = "abc123",
) -> PocPlan:
    return PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "minimatch@3.0.4"],
        install_hosts=["registry.npmjs.org"],
        trigger_cmd=["node", "trigger.js"],
        expected_trigger_exit=expected_exit,
        expected_trigger_sha256=expected_sha,
        files={"trigger.js": "process.stdout.write('REDOS_CONFIRMED\\n');"},
        template_id="npm__minimatch__CVE-2022-3517",
    )


def _trigger(
    exit_code: int = 0,
    sha: str = "abc123",
    timed_out: bool = False,
    duration_s: float = 1.5,
) -> EvidenceCapture:
    return EvidenceCapture(
        phase="trigger",
        exit_code=exit_code,
        stdout_sha256=sha,
        timed_out=timed_out,
        duration_s=duration_s,
    )


# ---------------------------------------------------------------------------
# EvidenceCapture construction
# ---------------------------------------------------------------------------

def test_evidence_capture_construction():
    ev = EvidenceCapture(
        phase="install",
        exit_code=0,
        stdout_sha256="deadbeef",
        timed_out=False,
        duration_s=2.3,
    )
    assert ev.phase == "install"
    assert ev.exit_code == 0
    assert ev.stdout_sha256 == "deadbeef"
    assert ev.timed_out is False
    assert ev.duration_s == 2.3


def test_evidence_capture_is_frozen():
    ev = EvidenceCapture(
        phase="trigger", exit_code=1, stdout_sha256="ff", timed_out=False, duration_s=0.1
    )
    with pytest.raises(AttributeError):
        ev.exit_code = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Verdict construction
# ---------------------------------------------------------------------------

def test_verdict_construction():
    ev = _trigger()
    v = Verdict(
        hypothesis_id="hyp-001",
        program_slug="test-prog",
        target_identifier="minimatch@3.0.4",
        vuln_class="dependency-cve",
        verdict=VERDICT_VERIFIED,
        reason="exit+sha match",
        strategy="templated",
        template_id="npm__minimatch__CVE-2022-3517",
        evidence=[ev],
        verified_at="2026-06-22T00:00:00Z",
    )
    assert v.hypothesis_id == "hyp-001"
    assert v.verdict == VERDICT_VERIFIED
    assert v.template_id == "npm__minimatch__CVE-2022-3517"
    assert len(v.evidence) == 1


def test_verdict_template_id_none():
    v = Verdict(
        hypothesis_id="hyp-002",
        program_slug="test-prog",
        target_identifier="some-pkg@1.0.0",
        vuln_class="dependency-cve",
        verdict=VERDICT_SKIPPED,
        reason="no-strategy",
        strategy="templated",
        template_id=None,
        evidence=[],
        verified_at="2026-06-22T00:00:00Z",
    )
    assert v.template_id is None


def test_verdict_is_frozen():
    v = Verdict(
        hypothesis_id="hyp-003",
        program_slug="prog",
        target_identifier="pkg@1.0",
        vuln_class="dependency-cve",
        verdict=VERDICT_ERROR,
        reason="sandbox error",
        strategy="templated",
        template_id=None,
        evidence=[],
        verified_at="2026-06-22T00:00:00Z",
    )
    with pytest.raises(AttributeError):
        v.verdict = VERDICT_VERIFIED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Verdict constants
# ---------------------------------------------------------------------------

def test_verdict_constants():
    assert VERDICT_VERIFIED == "verified"
    assert VERDICT_REFUTED == "refuted"
    assert VERDICT_SKIPPED == "skipped"
    assert VERDICT_ERROR == "error"


# ---------------------------------------------------------------------------
# derive_verdict — all four paths
# ---------------------------------------------------------------------------

def test_derive_verdict_verified():
    """exit_code and sha both match → VERDICT_VERIFIED."""
    plan = _plan(expected_exit=0, expected_sha="abc123")
    trigger = _trigger(exit_code=0, sha="abc123", timed_out=False)
    assert derive_verdict(trigger, plan) == VERDICT_VERIFIED


def test_derive_verdict_refuted_sha_mismatch():
    """sha mismatch (exit matches) → VERDICT_REFUTED."""
    plan = _plan(expected_exit=0, expected_sha="abc123")
    trigger = _trigger(exit_code=0, sha="wrongsha", timed_out=False)
    assert derive_verdict(trigger, plan) == VERDICT_REFUTED


def test_derive_verdict_refuted_exit_mismatch():
    """exit mismatch (sha matches) → VERDICT_REFUTED."""
    plan = _plan(expected_exit=0, expected_sha="abc123")
    trigger = _trigger(exit_code=1, sha="abc123", timed_out=False)
    assert derive_verdict(trigger, plan) == VERDICT_REFUTED


def test_derive_verdict_refuted_both_mismatch():
    """Both exit and sha mismatch → VERDICT_REFUTED."""
    plan = _plan(expected_exit=0, expected_sha="abc123")
    trigger = _trigger(exit_code=2, sha="different", timed_out=False)
    assert derive_verdict(trigger, plan) == VERDICT_REFUTED


def test_derive_verdict_error_timed_out():
    """timed_out=True → VERDICT_ERROR, regardless of exit/sha."""
    plan = _plan(expected_exit=0, expected_sha="abc123")
    # Even if exit_code and sha would otherwise match, timed_out wins
    trigger = _trigger(exit_code=0, sha="abc123", timed_out=True)
    assert derive_verdict(trigger, plan) == VERDICT_ERROR


def test_derive_verdict_error_timed_out_overrides_match():
    """timed_out takes priority over a would-be exit+sha match."""
    plan = _plan(expected_exit=0, expected_sha="abc123")
    trigger = _trigger(exit_code=0, sha="abc123", timed_out=True)
    result = derive_verdict(trigger, plan)
    assert result == VERDICT_ERROR
    assert result != VERDICT_VERIFIED


# ---------------------------------------------------------------------------
# Differential verdict helpers and tests
# ---------------------------------------------------------------------------


def _diff_plan():
    return PocPlan(
        ecosystem="npm", install_cmd=["npm", "install", "x@1"], install_hosts=["r"],
        trigger_cmd=["node", "t.js"], expected_trigger_exit=0, expected_trigger_sha256="confirmed",
        files={"t.js": "x"}, template_id="t",
        fixed_install_cmd=["npm", "install", "x@2"],
        expected_refuted_exit=1, expected_refuted_sha256="patched",
    )


def test_differential_verified():
    from verify.model import derive_differential_verdict, VERDICT_VERIFIED
    plan = _diff_plan()
    affected = _trigger(exit_code=0, sha="confirmed")
    fixed = _trigger(exit_code=1, sha="patched")
    assert derive_differential_verdict(affected, fixed, plan) == (VERDICT_VERIFIED, "discriminates")


def test_differential_no_discrimination_is_error():
    from verify.model import derive_differential_verdict, VERDICT_ERROR
    plan = _diff_plan()
    affected = _trigger(exit_code=0, sha="confirmed")
    fixed = _trigger(exit_code=0, sha="confirmed")  # fired on patched too -> slop
    assert derive_differential_verdict(affected, fixed, plan) == (VERDICT_ERROR, "no-discrimination")


def test_differential_affected_refuted():
    from verify.model import derive_differential_verdict, VERDICT_REFUTED
    plan = _diff_plan()
    affected = _trigger(exit_code=1, sha="patched")  # did NOT fire on vulnerable code
    fixed = _trigger(exit_code=1, sha="patched")
    assert derive_differential_verdict(affected, fixed, plan) == (VERDICT_REFUTED, "affected-not-vulnerable")


def test_differential_affected_indeterminate_is_error_not_refuted():
    """hb-be9: output matching NEITHER signature must NOT be laundered to refuted."""
    from verify.model import derive_differential_verdict, VERDICT_ERROR
    plan = _diff_plan()
    affected = _trigger(exit_code=137, sha="oom-garbage")  # infra failure
    fixed = _trigger(exit_code=1, sha="patched")
    assert derive_differential_verdict(affected, fixed, plan) == (VERDICT_ERROR, "affected-indeterminate")


def test_differential_fixed_indeterminate_is_error():
    from verify.model import derive_differential_verdict, VERDICT_ERROR
    plan = _diff_plan()
    affected = _trigger(exit_code=0, sha="confirmed")
    fixed = _trigger(exit_code=99, sha="weird")  # matches neither
    assert derive_differential_verdict(affected, fixed, plan) == (VERDICT_ERROR, "fixed-indeterminate")


def test_differential_timeout_is_error():
    from verify.model import derive_differential_verdict, VERDICT_ERROR
    plan = _diff_plan()
    affected = _trigger(timed_out=True)
    fixed = _trigger(exit_code=1, sha="patched")
    assert derive_differential_verdict(affected, fixed, plan) == (VERDICT_ERROR, "timeout")


def test_differential_fixed_side_timeout_is_error():
    from verify.model import derive_differential_verdict, VERDICT_ERROR
    plan = _diff_plan()
    affected = _trigger(exit_code=0, sha="confirmed")
    fixed = _trigger(timed_out=True)
    assert derive_differential_verdict(affected, fixed, plan) == (VERDICT_ERROR, "timeout")


def test_differential_degenerate_signatures_never_verified():
    """C1: if verified and refuted signatures are identical, the oracle must fail closed
    (VERDICT_ERROR / 'degenerate-signature') — never grant verified."""
    from verify.model import derive_differential_verdict, VERDICT_ERROR
    degenerate_plan = PocPlan(
        ecosystem="npm", install_cmd=["npm", "install", "x@1"], install_hosts=["r"],
        trigger_cmd=["node", "t.js"],
        expected_trigger_exit=0, expected_trigger_sha256="same_sentinel",
        files={"t.js": "x"}, template_id="t",
        fixed_install_cmd=["npm", "install", "x@2"],
        expected_refuted_exit=0, expected_refuted_sha256="same_sentinel",
    )
    # Even if the fixed run "matches" the refuted signature (because it IS the verified one),
    # the oracle must refuse to grant verified.
    affected = _trigger(exit_code=0, sha="same_sentinel")
    fixed = _trigger(exit_code=0, sha="same_sentinel")
    assert derive_differential_verdict(affected, fixed, degenerate_plan) == (VERDICT_ERROR, "degenerate-signature")
