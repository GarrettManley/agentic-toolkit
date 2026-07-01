"""Tests for Stage 7 huntr venue wiring (design §2.4): huntr aliases to the
manual-form dispatcher, but the resulting finding/ledger status must reflect that
only a human-completed manual hand-off occurred -- never a false, fully-confirmed
'submitted'.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_select_dispatcher_huntr_aliases_to_manual_form():
    import submit
    fn, is_manual = submit._select_dispatcher("huntr")
    assert fn is submit._dispatch_manual_form
    assert is_manual is True


def test_select_dispatcher_manual_form_itself():
    import submit
    fn, is_manual = submit._select_dispatcher("manual-form")
    assert fn is submit._dispatch_manual_form
    assert is_manual is True


def test_select_dispatcher_ghsa_is_not_manual_alias():
    import submit
    fn, is_manual = submit._select_dispatcher("ghsa")
    assert fn is submit._dispatch_ghsa
    assert is_manual is False


def test_select_dispatcher_unknown_venue_stubs():
    import submit
    fn, is_manual = submit._select_dispatcher("ibb-h1")
    ok, info = fn("FIND-2026-07-01-001", Path("."), {})
    assert ok is False
    assert is_manual is False


def test_status_for_dispatch_manual_alias_is_submitted_manual():
    import submit
    assert submit._status_for_dispatch(True) == "submitted-manual"


def test_status_for_dispatch_real_confirmed_is_submitted():
    import submit
    assert submit._status_for_dispatch(False) == "submitted"


def test_huntr_never_produces_bare_submitted_status():
    """Regression guard for the exact bug found in adversarial review: huntr must
    never reach the fully-confirmed 'submitted' status through this path."""
    import submit
    _, is_manual = submit._select_dispatcher("huntr")
    assert submit._status_for_dispatch(is_manual) == "submitted-manual"


def test_main_huntr_end_to_end_yields_submitted_manual_status(
    override_key_setup, clean_overrides, tmp_path, monkeypatch,
):
    """End-to-end coverage of main() itself (not just the pure-function units above,
    which is all this file otherwise covers) -- submit.py currently has zero test
    coverage before this plan, and main()'s actual PT-2 token-consumption + ledger
    + finding-status-write logic is the substance of a human-gated submission script
    this workspace's CLAUDE.md calls load-bearing. Exercises the full --venue huntr
    path with a real, validly-signed approval token."""
    import json
    import sys
    from datetime import datetime, timedelta, timezone
    import submit
    from lib.sign_verify import sign_token

    trace_id = "FIND-2026-07-01-001"
    finding_dir = tmp_path / trace_id
    finding_dir.mkdir()
    (finding_dir / "finding.md").write_text(
        "---\n"
        "trace_id: FIND-2026-07-01-001\n"
        "program_slug: huntr-npm-test-target\n"
        "status: ready-for-review\n"
        "---\n"
        "Finding body.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(submit, "FINDINGS_DIR", tmp_path)
    monkeypatch.setattr(submit, "SUBMISSIONS_TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(submit, "OVERRIDES_USED_DIR", tmp_path / "overrides-used")
    monkeypatch.setattr(submit, "_load_program_scope", lambda slug: {
        "submission": {"protocol": "manual-form", "endpoint": "https://huntr.com/repos/x/y"},
    })
    monkeypatch.setattr(submit, "_dispatch_manual_form",
                        lambda trace_id, finding_dir, scope_data: (True, "submitted-manual"))

    events: list[tuple[str, dict]] = []
    class _Cap:
        def append_event(self, et, **f):
            events.append((et, f)); return {}
    monkeypatch.setattr(submit, "ledger", _Cap(), raising=False)

    now = datetime.now(timezone.utc)
    payload = {
        "token_id": "apv-2026-07-01-001",
        "trace_id": trace_id,
        "venue": "huntr",
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_uses": 1,
    }
    payload["signature"] = sign_token(payload)
    submit.SUBMISSIONS_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    (submit.SUBMISSIONS_TOKENS_DIR / "apv-2026-07-01-001.json").write_text(
        json.dumps(payload), encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", [
        "submit.py", "--trace", trace_id, "--token", "apv-2026-07-01-001", "--venue", "huntr",
    ])
    rc = submit.main()
    assert rc == 0

    updated = (finding_dir / "finding.md").read_text(encoding="utf-8")
    assert "status: submitted-manual" in updated
    assert "status: submitted\n" not in updated

    event_types = [et for et, _ in events]
    assert "submission-attempted" in event_types
    assert "submission-succeeded" in event_types
    succeeded = next(f for et, f in events if et == "submission-succeeded")
    assert succeeded["outcome"] == "submitted-manual"
