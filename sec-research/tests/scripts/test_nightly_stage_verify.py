"""Tests for nightly.stage_verify delegation to verify.harness.verify_hypotheses.

Task 7 — wire stage_verify stub replacement.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# conftest puts scripts/ and hooks/ on sys.path already, but be explicit for
# any test runner that might not have loaded conftest first.
_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


# ---------------------------------------------------------------------------
# Test 1: stage_verify delegates to verify_hypotheses
# ---------------------------------------------------------------------------

def test_stage_verify_delegates(monkeypatch):
    """stage_verify must delegate entirely to nightly.verify_hypotheses.

    The monkeypatch targets nightly.verify_hypotheses (the name nightly calls),
    matching the pattern used in test_nightly_stage4b.py for generate_hypotheses.
    """
    import nightly

    sentinel = [{"hypothesis_id": "h-001", "verified": True, "verdict": "verified"}]
    called = {}

    def _fake(hypotheses, **kw):
        called["args"] = hypotheses
        return sentinel

    monkeypatch.setattr(nightly, "verify_hypotheses", _fake)

    h1 = {"hypothesis_id": "h-001", "program_slug": "pkg-a"}
    h2 = {"hypothesis_id": "h-002", "program_slug": "pkg-b"}
    result = nightly.stage_verify([h1, h2])

    assert result is sentinel, "stage_verify must return the value from verify_hypotheses"
    assert called["args"] == [h1, h2], "stage_verify must pass hypotheses list unchanged"


# ---------------------------------------------------------------------------
# Test 2: stage_briefing back-compat — verified counter uses 'verified' bool
# ---------------------------------------------------------------------------

def test_stage_briefing_verified_counter(tmp_path, monkeypatch):
    """stage_briefing counts entries where v.get('verified') is True.

    Constructs a verified list shaped like verify_hypotheses output and asserts
    the briefing's 'Verified candidates: N' line reflects the correct count.
    """
    from lib import paths as lib_paths
    import nightly

    # Redirect briefings to tmp_path so the test is isolated.
    monkeypatch.setattr(lib_paths, "RUNTIME_BRIEFINGS_DIR", tmp_path)
    monkeypatch.setattr(nightly, "RUNTIME_BRIEFINGS_DIR", tmp_path)

    verified = [
        {"hypothesis_id": "h-001", "verdict": "verified",   "verified": True},
        {"hypothesis_id": "h-002", "verdict": "refuted",    "verified": False},
        {"hypothesis_id": "h-003", "verdict": "skipped",    "verified": False},
        {"hypothesis_id": "h-004", "verdict": "verified",   "verified": True},
    ]

    path = nightly.stage_briefing(
        scopes={},
        recon=[],
        hypotheses=[],
        verified=verified,
        drafts=[],
    )

    content = path.read_text(encoding="utf-8")
    assert "Verified candidates: 2" in content, (
        f"Expected 'Verified candidates: 2' in briefing, got:\n{content}"
    )
