"""Tests for the unattended-eligible scope filter (design §2.3): the unattended
nightly-cron path must skip any scope not explicitly marked
rules.unattended_eligible=true, so a freshly-loaded supervised-only target isn't
silently reprocessed to full draft-finding completion by the next scheduled run.
run_supervised() is NOT filtered -- an explicit --supervised invocation IS the human
supervision itself, regardless of the flag.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_filter_skips_scope_without_rules_key_at_all():
    import nightly
    eligible, skipped = nightly._filter_unattended_eligible({"fresh-target": {}})
    assert eligible == {}
    assert skipped == ["fresh-target"]


def test_filter_skips_scope_with_empty_rules():
    import nightly
    eligible, skipped = nightly._filter_unattended_eligible({"fresh-target": {"rules": {}}})
    assert eligible == {}
    assert skipped == ["fresh-target"]


def test_filter_skips_scope_with_flag_explicitly_false():
    import nightly
    scopes = {"fresh-target": {"rules": {"unattended_eligible": False}}}
    eligible, skipped = nightly._filter_unattended_eligible(scopes)
    assert eligible == {}
    assert skipped == ["fresh-target"]


def test_filter_keeps_scope_explicitly_authorized():
    import nightly
    scopes = {"reviewed-target": {"rules": {"unattended_eligible": True}}}
    eligible, skipped = nightly._filter_unattended_eligible(scopes)
    assert eligible == scopes
    assert skipped == []


def test_run_unattended_only_processes_eligible_scopes(monkeypatch, tmp_path):
    """End-to-end: run_unattended() must not call stage_recon for a scope that isn't
    unattended-eligible, and must still process one that is."""
    import nightly
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(nightly, "RUNTIME_BRIEFINGS_DIR", tmp_path)
    monkeypatch.setattr(nightly, "RUNTIME_SCHEDULED_RUNS", tmp_path / "scheduled-runs.jsonl")
    monkeypatch.setattr(nightly, "load_all_scopes", lambda: {
        "fresh-target": {"rules": {}},
        "reviewed-target": {"rules": {"unattended_eligible": True}},
    })

    seen_scopes: dict = {}
    def _capture_recon(scopes):
        seen_scopes.update(scopes)
        return []
    monkeypatch.setattr(nightly, "stage_recon", _capture_recon)
    monkeypatch.setattr(nightly, "stage_hypothesize", lambda scopes, recon: [])
    monkeypatch.setattr(nightly, "stage_verify", lambda hyps: [])

    rc = nightly.run_unattended()
    assert rc == 0
    assert list(seen_scopes.keys()) == ["reviewed-target"]
