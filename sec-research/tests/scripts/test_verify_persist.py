"""Tests for verify.harness._persist and its wiring into verify_hypotheses.

Strict TDD: tests written BEFORE the implementation.
All tests use tmp_path as verdict_root; no real filesystem side-effects.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

import pytest

from verify.model import (
    VERDICT_VERIFIED,
    EvidenceCapture,
    Verdict,
)
from verify.strategy import PocPlan

import verify.harness as _harness


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SENTINEL = "REDOS_CONFIRMED\n"
_SHA = hashlib.sha256(_SENTINEL.encode()).hexdigest()


def _ev(*, phase: str, exit_code: int = 0) -> EvidenceCapture:
    return EvidenceCapture(
        phase=phase,
        exit_code=exit_code,
        stdout_sha256=_SHA,
        timed_out=False,
        duration_s=0.1,
    )


def _verdict(
    *,
    hypothesis_id: str = "HYP-2026-06-22-001",
    program_slug: str = "slug-a",
    verdict: str = VERDICT_VERIFIED,
    evidence: list[EvidenceCapture] | None = None,
) -> Verdict:
    return Verdict(
        hypothesis_id=hypothesis_id,
        program_slug=program_slug,
        target_identifier="pkg@1.0.0",
        vuln_class="dependency-cve",
        verdict=verdict,
        reason="test reason",
        strategy="fake",
        template_id="tmpl-001",
        evidence=evidence or [_ev(phase="install"), _ev(phase="trigger")],
        verified_at="2026-06-22T00:00:00Z",
    )


def _make_plan() -> PocPlan:
    return PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "pkg@1.0.0"],
        install_hosts=["registry.npmjs.org"],
        trigger_cmd=["node", "trigger.js"],
        expected_trigger_exit=0,
        expected_trigger_sha256=_SHA,
        files={"trigger.js": "process.exit(0);"},
        template_id="tmpl-001",
    )


# ---------------------------------------------------------------------------
# Ledger capture helper (same pattern as orchestrator tests)
# ---------------------------------------------------------------------------

class _LedgerCapture:
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
# Test: grouping — two slugs each get their own verdicts.json
# ---------------------------------------------------------------------------

def test_persist_groups_by_slug(tmp_path):
    """_persist groups verdicts by slug; each slug gets its own verdicts.json."""
    v_a1 = _verdict(hypothesis_id="HYP-001", program_slug="slug-a")
    v_a2 = _verdict(hypothesis_id="HYP-002", program_slug="slug-a")
    v_b1 = _verdict(hypothesis_id="HYP-003", program_slug="slug-b")

    _harness._persist([v_a1, v_a2, v_b1], verdict_root=tmp_path)

    path_a = tmp_path / "slug-a" / "verdicts.json"
    path_b = tmp_path / "slug-b" / "verdicts.json"

    assert path_a.exists(), "slug-a/verdicts.json must be created"
    assert path_b.exists(), "slug-b/verdicts.json must be created"

    data_a = json.loads(path_a.read_text(encoding="utf-8"))
    data_b = json.loads(path_b.read_text(encoding="utf-8"))

    assert len(data_a) == 2
    assert len(data_b) == 1

    a_ids = {d["hypothesis_id"] for d in data_a}
    assert a_ids == {"HYP-001", "HYP-002"}
    assert data_b[0]["hypothesis_id"] == "HYP-003"


# ---------------------------------------------------------------------------
# Test: JSON shape — asdict fields present, no "verified" key
# ---------------------------------------------------------------------------

def test_persist_json_shape(tmp_path):
    """Persisted dicts are asdict(Verdict); they do NOT carry a 'verified' key."""
    v = _verdict()
    _harness._persist([v], verdict_root=tmp_path)

    path = tmp_path / "slug-a" / "verdicts.json"
    records = json.loads(path.read_text(encoding="utf-8"))

    assert isinstance(records, list)
    assert len(records) == 1
    rec = records[0]

    # Required Verdict fields
    assert "hypothesis_id" in rec
    assert "program_slug" in rec
    assert "verdict" in rec
    assert "evidence" in rec
    assert isinstance(rec["evidence"], list)

    # Each evidence item must have EvidenceCapture fields
    for ev_dict in rec["evidence"]:
        assert "phase" in ev_dict
        assert "exit_code" in ev_dict
        assert "stdout_sha256" in ev_dict
        assert "timed_out" in ev_dict
        assert "duration_s" in ev_dict

    # "verified" key must NOT appear — it's only added in verify_hypotheses projection
    assert "verified" not in rec, "'verified' key must not be in persisted dicts"

    # Confirm it matches asdict exactly
    expected = asdict(v)
    assert rec == expected


# ---------------------------------------------------------------------------
# Test: empty list → no-op, no files written
# ---------------------------------------------------------------------------

def test_persist_empty_list_no_op(tmp_path):
    """_persist([]) writes nothing and does not crash."""
    _harness._persist([], verdict_root=tmp_path)

    # tmp_path should be empty — no subdirectories created
    contents = list(tmp_path.iterdir())
    assert contents == [], f"Expected no files written, got: {contents}"


# ---------------------------------------------------------------------------
# Test: best-effort — OSError does NOT propagate; emits verify-persist-error event
# ---------------------------------------------------------------------------

def test_persist_oserror_is_best_effort(tmp_path, monkeypatch):
    """An OSError during write must NOT escape _persist; a verify-persist-error ledger event is emitted."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    # Monkeypatch Path.write_text to raise OSError
    original_write_text = _harness.Path.write_text

    def exploding_write_text(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(_harness.Path, "write_text", exploding_write_text)

    v = _verdict()

    # Must not raise
    _harness._persist([v], verdict_root=tmp_path)

    # Must emit a verify-persist-error ledger event
    error_events = ledger_cap.events_of_type("verify-persist-error")
    assert len(error_events) >= 1, "Expected at least one verify-persist-error event"
    ev = error_events[0]
    assert "slug" in ev
    assert ev["slug"] == "slug-a"
    assert "error" in ev


# ---------------------------------------------------------------------------
# Test: integration — verify_hypotheses calls _persist; verdicts.json is written
# ---------------------------------------------------------------------------

def test_verify_hypotheses_wires_persist(tmp_path, monkeypatch):
    """verify_hypotheses must call _persist; after the call, verdicts.json exists for the slug."""
    ledger_cap = _LedgerCapture()
    monkeypatch.setattr(_harness, "ledger", type("L", (), {"append_event": staticmethod(ledger_cap)})())

    slug = "huntr-npm-minimatch"

    install_ev = EvidenceCapture(
        phase="install", exit_code=0, stdout_sha256=_SHA, timed_out=False, duration_s=0.1
    )
    trigger_ev = EvidenceCapture(
        phase="trigger", exit_code=0, stdout_sha256=_SHA, timed_out=False, duration_s=0.05
    )

    def fake_drive(plan, hid, slug_arg, *, runner, verdict_root):
        return install_ev, trigger_ev

    monkeypatch.setattr(_harness, "_drive_phased", fake_drive)

    class _FakeStrategy:
        name = "fake"

        def supports(self, h: dict) -> bool:
            return True

        def build_plan(self, h: dict) -> PocPlan:
            return _make_plan()

    hyp = {
        "hypothesis_id": "HYP-2026-06-22-001",
        "program_slug": slug,
        "target": {"identifier": "minimatch@3.0.4"},
        "vuln_class": "dependency-cve",
    }

    results = _harness.verify_hypotheses(
        [hyp],
        strategy=_FakeStrategy(),
        verdict_root=tmp_path,
    )

    # Return value is unchanged — still the projected list with "verified" key
    assert len(results) == 1
    assert results[0]["verdict"] == VERDICT_VERIFIED
    assert results[0]["verified"] is True

    # verdicts.json must have been written
    verdicts_path = tmp_path / slug / "verdicts.json"
    assert verdicts_path.exists(), f"verdicts.json not found at {verdicts_path}"

    records = json.loads(verdicts_path.read_text(encoding="utf-8"))
    assert len(records) == 1
    rec = records[0]
    assert rec["hypothesis_id"] == "HYP-2026-06-22-001"
    assert rec["program_slug"] == slug
    assert "verified" not in rec, "persisted dict must not carry 'verified' key"
