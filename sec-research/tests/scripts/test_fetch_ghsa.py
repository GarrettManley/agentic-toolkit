"""Tests for scripts/fetchers/ghsa.py.

TDD: written before the implementation exists. Run with:
    python -m pytest tests/scripts/test_fetch_ghsa.py -v
from the sec-research/ directory.
"""
from pathlib import Path

import pytest

from lib.schema_validate import validate_program

FX = Path(__file__).resolve().parent.parent / "fixtures" / "ghsa-fetch"


def test_ghsa_fixture_produces_valid_scope(tmp_programs):
    from fetchers import ghsa
    res = ghsa.fetch("acme-org/acme-repo",
                     from_fixture=FX / "repos_acme-org_acme-repo.json",
                     advisories_fixture=FX / "security_advisories.json")
    assert res.ok
    ok, errors = validate_program(res.data)
    assert ok, errors
    assert res.data["program_slug"] == "ghsa-acme-org-acme-repo"
    assert res.data["venue"] == "ghsa"
    assert res.data["submission"]["protocol"] == "ghsa-cli"
    assert res.data["loaded_from"] == "https://github.com/acme-org/acme-repo/security/advisories"
    repos = [e for e in res.data["in_scope"] if e["asset_type"] == "repo"]
    assert repos[0]["identifier"] == "github.com/acme-org/acme-repo"
    assert all("max_payout_usd" not in e for e in res.data["in_scope"])  # GHSA has no payout


def test_ghsa_gh_error_returns_clean_failure(tmp_programs, monkeypatch):
    from fetchers import ghsa, _http
    def boom(path, **kw):
        raise _http.GhApiError("gh: not authenticated")
    monkeypatch.setattr(_http, "gh_api_json", boom)
    res = ghsa.fetch("acme-org/acme-repo")  # live path -> stubbed error
    assert res.ok is False and res.data is None
    assert any("gh" in w.lower() for w in res.warnings)


def test_ghsa_bad_identifier(tmp_programs):
    from fetchers import ghsa
    res = ghsa.fetch("noslash", from_fixture=FX / "repos_acme-org_acme-repo.json")
    assert res.ok is False
