"""Tests for scripts/triage/persist.py — persist_triage writes triage.json and emits ledger event.

TDD: tests written before implementation.
Ledger isolation: monkeypatch scripts.triage.persist.ledger (same pattern as
test_verify_persist.py patches verify.harness.ledger) so the real
submissions/ledger.jsonl is never touched.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.triage.persist import persist_triage
from scripts.triage.model import TriageResult, DedupInfo, TRIAGE_DUPLICATE, TRIAGE_NOVEL
from scripts.verify.model import Verdict, VERDICT_VERIFIED


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _result(status: str, template_id: str) -> TriageResult:
    v = Verdict(
        hypothesis_id="h",
        program_slug="p",
        target_identifier="minimatch@3.0.4",
        vuln_class="dependency-cve",
        verdict=VERDICT_VERIFIED,
        reason="ok",
        strategy="templated",
        template_id=template_id,
        evidence=[],
        verified_at="t",
    )
    d = DedupInfo(
        checked_against=["CVE-2022-3517"],
        duplicates_found=[],
        checked_at="t",
        source="recon-osv",
    )
    return TriageResult(verdict=v, is_novel=(status == TRIAGE_NOVEL), dedup=d, triage_status=status)


class _LedgerCapture:
    """Drop-in replacement for the ledger module; records calls without touching disk."""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def append_event(self, event_type: str, **fields: Any) -> dict:
        self.events.append((event_type, fields))
        return {"entry_id": "led-test", "event_type": event_type, **fields}

    def event_types(self) -> list[str]:
        return [e[0] for e in self.events]

    def events_of_type(self, etype: str) -> list[dict]:
        return [fields for (et, fields) in self.events if et == etype]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_persist_writes_triage_json(tmp_path: Path, monkeypatch):
    """persist_triage writes runtime/triage/<slug>/triage.json with correct shape."""
    import scripts.triage.persist as _persist_mod

    cap = _LedgerCapture()
    monkeypatch.setattr(_persist_mod, "ledger", cap)

    results = [
        _result(TRIAGE_DUPLICATE, "npm:minimatch:CVE-2022-3517"),
        _result(TRIAGE_NOVEL, "npm:left-pad:CVE-2099-0001"),
    ]
    out = persist_triage("huntr-npm-minimatch", results, runtime_root=tmp_path)

    assert out == tmp_path / "triage" / "huntr-npm-minimatch" / "triage.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert {r["triage_status"] for r in payload} == {"duplicate", "novel"}
    assert payload[0]["verdict"]["target_identifier"] == "minimatch@3.0.4"


def test_persist_emits_ledger_event(tmp_path: Path, monkeypatch):
    """persist_triage appends exactly one triage-summary ledger event with slug and counts."""
    import scripts.triage.persist as _persist_mod

    cap = _LedgerCapture()
    monkeypatch.setattr(_persist_mod, "ledger", cap)

    results = [
        _result(TRIAGE_DUPLICATE, "npm:minimatch:CVE-2022-3517"),
        _result(TRIAGE_NOVEL, "npm:left-pad:CVE-2099-0001"),
        _result(TRIAGE_NOVEL, "npm:left-pad:CVE-2099-0002"),
    ]
    persist_triage("huntr-npm-minimatch", results, runtime_root=tmp_path)

    summary_events = cap.events_of_type("triage-summary")
    assert len(summary_events) == 1, f"Expected 1 triage-summary event, got: {cap.event_types()}"

    ev = summary_events[0]
    assert ev["slug"] == "huntr-npm-minimatch"
    assert ev["novel"] == 2
    assert ev["duplicate"] == 1
    assert ev["total"] == 3


def test_persist_returns_path(tmp_path: Path, monkeypatch):
    """persist_triage returns the Path to the written triage.json."""
    import scripts.triage.persist as _persist_mod

    cap = _LedgerCapture()
    monkeypatch.setattr(_persist_mod, "ledger", cap)

    results = [_result(TRIAGE_NOVEL, "npm:x:CVE-2099-9999")]
    out = persist_triage("my-slug", results, runtime_root=tmp_path)

    assert isinstance(out, Path)
    assert out.exists()
    assert out.name == "triage.json"
    assert out.parent.name == "my-slug"


def test_persist_uses_default_runtime_when_none(monkeypatch):
    """With runtime_root=None, persist_triage resolves to the real runtime dir (smoke check)."""
    import scripts.triage.persist as _persist_mod

    cap = _LedgerCapture()
    monkeypatch.setattr(_persist_mod, "ledger", cap)

    # Just verify the returned path has the right structure
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr(_persist_mod, "_DEFAULT_RUNTIME", Path(td))
        out = persist_triage("test-slug", [_result(TRIAGE_NOVEL, "t")], runtime_root=None)
        assert out == Path(td) / "triage" / "test-slug" / "triage.json"
        assert out.exists()
