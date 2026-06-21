"""Tests for scripts/fetchers/ibb.py — IBB-on-HackerOne scope fetcher.

All tests are offline-only: they feed authored fixture files that approximate the
H1 structured_scopes API shape. The fixture→scope MAPPING is what is under test.
⚠️  Reconcile the fixture shape against a real api.hackerone.com response (requires
    an H1 token) before trusting the parser in production.
"""
from pathlib import Path

from lib.schema_validate import validate_program

FX = Path(__file__).resolve().parent.parent / "fixtures" / "ibb-fetch"


def test_ibb_bounty_eligible_asset_in_scope(tmp_programs):
    from fetchers import ibb
    res = ibb.fetch("django", from_fixture=FX / "structured_scopes_django.json")
    assert res.ok and not res.draft
    ok, errors = validate_program(res.data)
    assert ok, errors
    assert res.data["program_slug"] == "ibb-django"
    assert res.data["venue"] == "ibb-h1"
    assert res.data["submission"]["protocol"] == "manual-form"  # Stage-2 stop-gap (h1-api in Stage 7)
    assert res.data["rules"]["embargo_period_days"] == 90
    in_ids = [e["identifier"] for e in res.data["in_scope"]]
    out_ids = [e["identifier"] for e in res.data["out_of_scope"]]
    assert "django" in in_ids
    assert "vdp-only-asset" not in in_ids       # VDP-only never silently in-scope
    assert "vdp-only-asset" in out_ids          # routed to out_of_scope with a reason
    assert all(e.get("reason") for e in res.data["out_of_scope"])


def test_ibb_token_denied_falls_back_to_draft(tmp_programs):
    from fetchers import ibb
    res = ibb.fetch("django", from_fixture=FX / "forbidden_403.json")
    assert res.draft is True
    assert res.data is not None  # scaffold skeleton for manual completion
    assert any("reputation" in w.lower() or "manual" in w.lower() or "denied" in w.lower()
               for w in res.warnings)
    ok, errors = validate_program(res.data)
    assert ok, f"draft skeleton is schema-invalid: {errors}"


def test_ibb_no_credential_falls_back_to_draft(tmp_programs, monkeypatch):
    from fetchers import ibb
    monkeypatch.setattr(ibb, "get_credential", lambda _: None)
    res = ibb.fetch("django")
    assert res.draft is True
    assert res.data is not None
    assert len(res.warnings) > 0 and any(
        "credential" in w.lower() or "no hackerone" in w.lower() for w in res.warnings
    )
    ok, errors = validate_program(res.data)
    assert ok, f"draft skeleton is schema-invalid: {errors}"
