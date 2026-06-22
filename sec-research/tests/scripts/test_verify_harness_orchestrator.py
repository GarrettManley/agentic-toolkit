"""Tests for verify.harness.verify_hypotheses — batch orchestrator.

Strict TDD: these tests were written BEFORE the implementation.
All tests use duck-typed fake strategies and monkeypatch verify.harness._drive_phased
to isolate the orchestration logic from sandbox execution.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import pytest

from hooks.lib.policy import ScopeViolation
from sandbox.runner import SandboxError
from verify.model import (
    VERDICT_ERROR,
    VERDICT_REFUTED,
    VERDICT_SKIPPED,
    VERDICT_VERIFIED,
    EvidenceCapture,
)
from verify.strategy import PocPlan, SeedIncomplete


# ---------------------------------------------------------------------------
# Helpers — build deterministic PocPlan and EvidenceCapture fixtures
# ---------------------------------------------------------------------------

_SENTINEL = "REDOS_CONFIRMED\n"
_SHA = hashlib.sha256(_SENTINEL.encode()).hexdigest()

_MISMATCH_SHA = "0" * 64  # a sha256 that will never match _SHA


def _make_plan(template_id: str = "npm__minimatch__CVE-2022-3517") -> PocPlan:
    return PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "minimatch@3.0.4"],
        install_hosts=["registry.npmjs.org"],
        trigger_cmd=["node", "trigger.js"],
        expected_trigger_exit=0,
        expected_trigger_sha256=_SHA,
        files={"trigger.js": "process.stdout.write('REDOS_CONFIRMED\\n'); process.exit(0);"},
        template_id=template_id,
    )


def _ev(*, phase: str = "install", exit_code: int = 0, sha: str = _SHA,
        timed_out: bool = False, duration_s: float = 0.1) -> EvidenceCapture:
    return EvidenceCapture(
        phase=phase,
        exit_code=exit_code,
        stdout_sha256=sha,
        timed_out=timed_out,
        duration_s=duration_s,
    )


_INSTALL_EV = _ev(phase="install")
_TRIGGER_EV_VERIFIED = _ev(phase="trigger", exit_code=0, sha=_SHA)
_TRIGGER_EV_REFUTED = _ev(phase="trigger", exit_code=0, sha=_MISMATCH_SHA)
_TRIGGER_EV_TIMED_OUT = _ev(phase="trigger", timed_out=True)


# ---------------------------------------------------------------------------
# Fake strategy — duck-typed; does NOT inherit PocStrategy Protocol
# ---------------------------------------------------------------------------

class _FakeStrategy:
    """Minimal duck-type satisfying the PocStrategy Protocol surface."""

    name: str = "fake"

    def __init__(self, *, supports: bool = True, plan: PocPlan | None = None,
                 raises: Exception | None = None):
        self._supports = supports
        self._plan = plan or _make_plan()
        self._raises = raises

    def supports(self, hypothesis: dict) -> bool:
        return self._supports

    def build_plan(self, hypothesis: dict) -> PocPlan:
        if self._raises is not None:
            raise self._raises
        return self._plan


# ---------------------------------------------------------------------------
# Minimal hypothesis fixture
# ---------------------------------------------------------------------------

def _hyp(hid: str = "HYP-2026-06-22-001", slug: str = "huntr-npm-minimatch") -> dict:
    return {
        "hypothesis_id": hid,
        "program_slug": slug,
        "target": {"identifier": "minimatch@3.0.4"},
        "vuln_class": "dependency-cve",
    }


# ---------------------------------------------------------------------------
# Ledger capture helper
# ---------------------------------------------------------------------------

class _LedgerCapture:
    """Captures calls to ledger.append_event."""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def __call__(self, event_type: str, **fields: Any) -> dict:
        self.events.append((event_type, fields))
        return {"entry_id": "led-test", "event_type": event_type, **fields}

    def event_types(self) -> list[str]:
        return [e[0] for e in self.events]

    def events_of_type(self, etype: str) -> list[dict]:
        return [fields for (et, fields) in self.events if et == etype]


# ---------------------------------------------------------------------------
# Import the module-under-test after fixtures are defined
# ---------------------------------------------------------------------------

import verify.harness as _harness  # noqa: E402 — must be after sys.path is set by conftest


# ---------------------------------------------------------------------------
# Test: verified path — exit+sha match
# ---------------------------------------------------------------------------

def test_verified_verdict(monkeypatch):
    """When _drive_phased returns a trigger that matches plan → verdict=='verified', verified==True."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True)

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    results = _harness.verify_hypotheses([_hyp()], strategy=strategy)

    assert len(results) == 1
    r = results[0]
    assert r["verdict"] == VERDICT_VERIFIED
    assert r["verified"] is True
    assert "verify-verdict" in ledger_cap.event_types()
    evs = ledger_cap.events_of_type("verify-verdict")
    assert evs[0]["verdict"] == VERDICT_VERIFIED


# ---------------------------------------------------------------------------
# Test: refuted path — sha mismatch
# ---------------------------------------------------------------------------

def test_refuted_verdict(monkeypatch):
    """When trigger sha doesn't match plan.expected → verdict=='refuted', verified==False."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True)

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        return _INSTALL_EV, _TRIGGER_EV_REFUTED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    results = _harness.verify_hypotheses([_hyp()], strategy=strategy)

    assert len(results) == 1
    r = results[0]
    assert r["verdict"] == VERDICT_REFUTED
    assert r["verified"] is False


# ---------------------------------------------------------------------------
# Test: error path — timed_out
# ---------------------------------------------------------------------------

def test_error_verdict_timed_out(monkeypatch):
    """When trigger_ev.timed_out=True → verdict=='error'."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True)

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        return _INSTALL_EV, _TRIGGER_EV_TIMED_OUT

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    results = _harness.verify_hypotheses([_hyp()], strategy=strategy)

    assert len(results) == 1
    assert results[0]["verdict"] == VERDICT_ERROR


# ---------------------------------------------------------------------------
# Test: skipped — no matching strategy
# ---------------------------------------------------------------------------

def test_skipped_no_strategy(monkeypatch):
    """strategy.supports → False → verdict=='skipped', reason mentions no strategy, _drive_phased NOT called."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    drive_calls = []

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        drive_calls.append((hid, slug))
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    strategy = _FakeStrategy(supports=False)
    results = _harness.verify_hypotheses([_hyp()], strategy=strategy)

    assert len(results) == 1
    r = results[0]
    assert r["verdict"] == VERDICT_SKIPPED
    assert r["verified"] is False
    assert "no" in r["reason"].lower() or "strategy" in r["reason"].lower()
    assert "verify-no-strategy" in ledger_cap.event_types()
    assert len(drive_calls) == 0, "_drive_phased must NOT be called when strategy doesn't support"


# ---------------------------------------------------------------------------
# Test: skipped — seed incomplete
# ---------------------------------------------------------------------------

def test_skipped_seed_incomplete(monkeypatch):
    """build_plan raises SeedIncomplete → verdict=='skipped', reason includes missing list, verify-seed-incomplete event."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    missing = ["package_name", "candidate_cve_id"]
    strategy = _FakeStrategy(supports=True, raises=SeedIncomplete(missing))

    drive_calls = []

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        drive_calls.append((hid, slug))
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    results = _harness.verify_hypotheses([_hyp()], strategy=strategy)

    assert len(results) == 1
    r = results[0]
    assert r["verdict"] == VERDICT_SKIPPED
    assert r["verified"] is False
    # reason should mention the missing fields
    assert "package_name" in r["reason"] or "missing" in r["reason"].lower()
    assert "verify-seed-incomplete" in ledger_cap.event_types()
    seed_evs = ledger_cap.events_of_type("verify-seed-incomplete")
    assert seed_evs[0]["missing"] == missing
    assert len(drive_calls) == 0


# ---------------------------------------------------------------------------
# Test: SandboxError per-item isolation (2-item batch)
# ---------------------------------------------------------------------------

def test_sandbox_error_isolation_two_item_batch(monkeypatch):
    """First item raises SandboxError; second succeeds (verified). Batch returns 2 verdicts."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True)

    call_count = [0]

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        call_count[0] += 1
        if call_count[0] == 1:
            raise SandboxError("docker daemon not reachable")
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    hyp1 = _hyp("HYP-001", "slug-a")
    hyp2 = _hyp("HYP-002", "slug-b")
    results = _harness.verify_hypotheses([hyp1, hyp2], strategy=strategy)

    assert len(results) == 2
    assert results[0]["verdict"] == VERDICT_ERROR
    assert results[1]["verdict"] == VERDICT_VERIFIED
    assert results[1]["verified"] is True
    assert "verify-sandbox-error" in ledger_cap.event_types()


# ---------------------------------------------------------------------------
# Test: ScopeViolation propagates uncaught
# ---------------------------------------------------------------------------

def test_scope_violation_propagates(monkeypatch):
    """_drive_phased raising ScopeViolation must propagate out of verify_hypotheses uncaught."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True)

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        raise ScopeViolation(
            url="https://evil.example.com/payload",
            host="evil.example.com",
            reason="host not in scope",
            rule_id="PT-1",
        )

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    with pytest.raises(ScopeViolation):
        _harness.verify_hypotheses([_hyp()], strategy=strategy)


# ---------------------------------------------------------------------------
# Test: every dict has `verified` bool key
# ---------------------------------------------------------------------------

def test_every_result_has_verified_bool(monkeypatch):
    """Every returned dict must have a 'verified' key that is a bool."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    # Mix of outcomes: one verified, one skipped-no-strategy, one SandboxError
    call_count = [0]

    class _MixedStrategy:
        name = "mixed"

        def supports(self, h: dict) -> bool:
            return h["hypothesis_id"] != "HYP-003"

        def build_plan(self, h: dict) -> PocPlan:
            return _make_plan()

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        call_count[0] += 1
        if hid == "HYP-002":
            raise SandboxError("sandbox fail")
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    hyps = [
        _hyp("HYP-001", "slug-1"),
        _hyp("HYP-002", "slug-2"),
        _hyp("HYP-003", "slug-3"),
    ]
    results = _harness.verify_hypotheses(hyps, strategy=_MixedStrategy())

    assert len(results) == 3
    for r in results:
        assert "verified" in r, f"'verified' key missing from {r}"
        assert isinstance(r["verified"], bool), f"'verified' is not bool in {r}"


# ---------------------------------------------------------------------------
# Test: strategy.name is carried into the verdict dict
# ---------------------------------------------------------------------------

def test_strategy_name_in_verdict(monkeypatch):
    """Returned verdict dict 'strategy' field must equal the strategy's name attribute."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    class _NamedStrategy:
        name = "my-custom-strategy"

        def supports(self, h: dict) -> bool:
            return True

        def build_plan(self, h: dict) -> PocPlan:
            return _make_plan()

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    results = _harness.verify_hypotheses([_hyp()], strategy=_NamedStrategy())

    assert results[0]["strategy"] == "my-custom-strategy"


# ---------------------------------------------------------------------------
# Test: verify-started ledger event emitted with count
# ---------------------------------------------------------------------------

def test_verify_started_event(monkeypatch):
    """A 'verify-started' ledger event must be emitted at the top of verify_hypotheses."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=False)  # simplest path to avoid drive_phased

    monkeypatch.setattr(_harness, "_drive_phased", lambda *a, **kw: (_INSTALL_EV, _TRIGGER_EV_VERIFIED))

    _harness.verify_hypotheses([_hyp(), _hyp("HYP-002", "slug-2")], strategy=strategy)

    started = ledger_cap.events_of_type("verify-started")
    assert len(started) == 1
    assert started[0]["count"] == 2


# ---------------------------------------------------------------------------
# Test: TemplatedPocStrategy.name == "templated"
# ---------------------------------------------------------------------------

def test_templated_strategy_name():
    """TemplatedPocStrategy must have name == 'templated'."""
    from verify.templated import TemplatedPocStrategy
    assert TemplatedPocStrategy.name == "templated"
    # Also verify on instance
    assert TemplatedPocStrategy().name == "templated"


# ---------------------------------------------------------------------------
# Test: LLMPocStrategy.name == "llm"
# ---------------------------------------------------------------------------

def test_llm_strategy_name():
    """LLMPocStrategy must have name == 'llm'."""
    from verify.llm_strategy import LLMPocStrategy
    assert LLMPocStrategy.name == "llm"
    assert LLMPocStrategy().name == "llm"


# ---------------------------------------------------------------------------
# Test: verify-verdict event carries template_id
# ---------------------------------------------------------------------------

def test_verify_verdict_event_carries_template_id(monkeypatch):
    """The verify-verdict ledger event must carry the template_id from the plan."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True, plan=_make_plan("some-template-id"))

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    _harness.verify_hypotheses([_hyp()], strategy=strategy)

    evs = ledger_cap.events_of_type("verify-verdict")
    assert evs[0]["template_id"] == "some-template-id"


# ---------------------------------------------------------------------------
# Test: empty hypotheses list → empty results, verify-started with count=0
# ---------------------------------------------------------------------------

def test_empty_input_returns_empty(monkeypatch):
    """verify_hypotheses([]) → [] with a verify-started event count=0."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True)
    monkeypatch.setattr(_harness, "_drive_phased", lambda *a, **kw: (_INSTALL_EV, _TRIGGER_EV_VERIFIED))

    results = _harness.verify_hypotheses([], strategy=strategy)

    assert results == []
    started = ledger_cap.events_of_type("verify-started")
    assert started[0]["count"] == 0


# ---------------------------------------------------------------------------
# Test: target_identifier includes version when version_or_revision is present (I-2)
# ---------------------------------------------------------------------------

def test_target_identifier_includes_version(monkeypatch):
    """Verdict.target_identifier must be 'identifier@version' when version_or_revision is set."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True)

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    hyp = {
        "hypothesis_id": "HYP-ver-001",
        "program_slug": "test-slug",
        "target": {
            "identifier": "minimatch",
            "version_or_revision": "3.0.4",
        },
        "vuln_class": "dependency-cve",
    }

    results = _harness.verify_hypotheses([hyp], strategy=strategy)

    assert len(results) == 1
    assert results[0]["target_identifier"] == "minimatch@3.0.4"


def test_target_identifier_without_version(monkeypatch):
    """Verdict.target_identifier falls back to bare identifier when version_or_revision absent."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    strategy = _FakeStrategy(supports=True)

    def fake_drive(plan, hid, slug, *, runner, verdict_root):
        return _INSTALL_EV, _TRIGGER_EV_VERIFIED

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    hyp = {
        "hypothesis_id": "HYP-ver-002",
        "program_slug": "test-slug",
        "target": {"identifier": "minimatch@3.0.4"},
        "vuln_class": "dependency-cve",
    }

    results = _harness.verify_hypotheses([hyp], strategy=strategy)

    assert len(results) == 1
    assert results[0]["target_identifier"] == "minimatch@3.0.4"
