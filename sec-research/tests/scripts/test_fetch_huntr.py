"""Tests for scripts/fetchers/huntr.py.

TDD: written before the implementation exists. Run with:
    python -m pytest tests/scripts/test_fetch_huntr.py -v
from the sec-research/ directory.
"""
from pathlib import Path

from lib.schema_validate import validate_program

FX = Path(__file__).resolve().parent.parent / "fixtures" / "huntr-fetch"


def test_huntr_fixture_produces_valid_scope(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg", from_fixture=FX / "repo_acme-org_acme-pkg.html")
    assert res.ok and res.data and not res.draft
    ok, errors = validate_program(res.data)
    assert ok, errors
    assert res.data["program_slug"] == "huntr-acme-org-acme-pkg"
    assert res.data["venue"] == "huntr"
    assert res.data["venue_program_id"] == "acme-org/acme-pkg"
    assert res.data["loaded_from"] == "https://huntr.com/repos/acme-org/acme-pkg"
    assert res.data["submission"]["protocol"] == "manual-form"
    assert res.data["rules"]["ai_disclosure_required"] is True
    assert res.data["rules"]["rate_limit_per_min"] == 60
    assert "captured" in res.data["rules"]["notes"].lower()
    pkgs = [e for e in res.data["in_scope"] if e["asset_type"] == "package"]
    repos = [e for e in res.data["in_scope"] if e["asset_type"] == "repo"]
    assert pkgs[0]["ecosystem"] == "npm"
    assert repos[0]["identifier"] == "github.com/acme-org/acme-pkg"


def test_huntr_probes_manifest_when_page_silent(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg",
                      from_fixture=FX / "repo_no_ecosystem.html",
                      manifest_fixture=FX / "contents_npm.json")
    pkg = next(e for e in res.data["in_scope"] if e["asset_type"] == "package")
    assert pkg["ecosystem"] == "npm"  # inferred from package.json in contents listing


def test_huntr_ecosystem_miss_omits_field_and_warns(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/mystery",
                      from_fixture=FX / "repo_unknown_ecosystem.html",
                      manifest_fixture=FX / "contents_empty.json")
    pkg = next(e for e in res.data["in_scope"] if e["asset_type"] == "package")
    assert "ecosystem" not in pkg
    assert any("ecosystem" in w for w in res.warnings)
    ok, _ = validate_program(res.data)
    assert ok  # still schema-valid with ecosystem omitted


def test_huntr_unparseable_markup_returns_clean_error(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg", from_fixture=FX / "garbage.html")
    assert res.ok is False and res.data is None
    assert any("parse" in w.lower() for w in res.warnings)


def test_huntr_bad_identifier(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("no-slash", from_fixture=FX / "repo_acme-org_acme-pkg.html")
    assert res.ok is False
