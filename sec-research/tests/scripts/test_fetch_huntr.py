"""Tests for scripts/fetchers/huntr.py.

Reconciled 2026-06-30 (hb-dzu): huntr migrated to the Next.js App Router. The
repo page no longer embeds a Next.js data blob or any structured repo metadata
(ecosystem / display_name / repository_url). Existence is confirmed from the
server-rendered <head> og:url canonical meta (present + matching for a real repo;
ABSENT on the 404 page). Ecosystem comes only from the GitHub manifest probe.
Fixtures carry the real <head> shapes from live captures (runtime/dzu-evidence/).
"""
from pathlib import Path

from lib.schema_validate import validate_program

FX = Path(__file__).resolve().parent.parent / "fixtures" / "huntr-fetch"


def test_huntr_live_shape_with_manifest_produces_valid_scope(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg",
                      from_fixture=FX / "repo_acme-org_acme-pkg.html",
                      manifest_fixture=FX / "contents_npm.json")
    assert res.ok and res.data and not res.draft
    ok, errors = validate_program(res.data)
    assert ok, errors
    assert res.data["program_slug"] == "huntr-acme-org-acme-pkg"
    assert res.data["venue"] == "huntr"
    assert res.data["venue_program_id"] == "acme-org/acme-pkg"
    assert res.data["loaded_from"] == "https://huntr.com/repos/acme-org/acme-pkg"
    assert res.data["display_name"] == "acme-org — acme-pkg"  # default; page has none
    assert res.data["submission"]["protocol"] == "manual-form"
    assert res.data["rules"]["ai_disclosure_required"] is True
    assert res.data["rules"]["rate_limit_per_min"] == 60
    assert "captured" in res.data["rules"]["notes"].lower()
    pkgs = [e for e in res.data["in_scope"] if e["asset_type"] == "package"]
    repos = [e for e in res.data["in_scope"] if e["asset_type"] == "repo"]
    assert pkgs[0]["ecosystem"] == "npm"  # from the manifest probe, not the page
    assert repos[0]["identifier"] == "github.com/acme-org/acme-pkg"


def test_huntr_real_capture_head_confirms_existence(tmp_programs):
    """The trimmed real isaacs/minimatch <head> must satisfy the existence check."""
    from fetchers import huntr
    res = huntr.fetch("isaacs/minimatch",
                      from_fixture=FX / "repo_isaacs_minimatch_live.html",
                      manifest_fixture=FX / "contents_npm.json")
    assert res.ok, res.warnings
    ok, errors = validate_program(res.data)
    assert ok, errors


def test_huntr_ecosystem_miss_omits_field_and_warns(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/mystery",
                      from_fixture=FX / "repo_unknown_ecosystem.html",
                      manifest_fixture=FX / "contents_empty.json")
    assert res.ok, res.warnings
    pkg = next(e for e in res.data["in_scope"] if e["asset_type"] == "package")
    assert "ecosystem" not in pkg
    assert any("ecosystem" in w for w in res.warnings)
    ok, _ = validate_program(res.data)
    assert ok


def test_huntr_rejects_404_page(tmp_programs):
    """huntr serves HTTP 200 for nonexistent repos; the 404 page has no og:url,
    so existence must be rejected on the og:url signal, not the status code."""
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg", from_fixture=FX / "repo_not_found_404.html")
    assert res.ok is False and res.data is None
    assert any("page shape" in w.lower() or "og:url" in w.lower() for w in res.warnings)


def test_huntr_unparseable_markup_returns_clean_error(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg", from_fixture=FX / "garbage.html")
    assert res.ok is False and res.data is None
    assert any("page shape" in w.lower() or "og:url" in w.lower() for w in res.warnings)


def test_huntr_bad_identifier(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("no-slash", from_fixture=FX / "repo_acme-org_acme-pkg.html")
    assert res.ok is False
    assert any("identifier" in w.lower() for w in res.warnings)
