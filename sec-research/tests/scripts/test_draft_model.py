"""Tests for scripts/draft/model.py — DraftResult, FindingDoc, next_trace_id."""
from pathlib import Path
from scripts.draft.model import next_trace_id, FindingDoc, DraftResult


def test_next_trace_id_first(tmp_path):
    assert next_trace_id(tmp_path, today="2026-06-22") == "FIND-2026-06-22-001"


def test_next_trace_id_increments(tmp_path):
    (tmp_path / "FIND-2026-06-22-001-foo").mkdir()
    (tmp_path / "FIND-2026-06-22-002-bar").mkdir()
    assert next_trace_id(tmp_path, today="2026-06-22") == "FIND-2026-06-22-003"


def test_findingdoc_and_draftresult():
    d = FindingDoc(frontmatter={"trace_id": "x"}, body="b", status="draft-complete")
    assert d.status == "draft-complete"
    r = DraftResult(trace_id="FIND-2026-06-22-001", path="findings/...", status="draft-complete")
    assert r.trace_id.startswith("FIND-")
