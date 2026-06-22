from pathlib import Path

from recon.deps import Closure, Dep
from recon.metadata import AssetMetadata
from recon.clone import CloneResult
from recon.advisories import Advisory


def _closure():
    return Closure(direct=[Dep("lodash", "4.17.21", "npm")],
                   deps=[Dep("lodash", "4.17.21", "npm")],
                   lockfile="package-lock.json", no_lockfile=False,
                   truncated=False, total_before_cap=1)


def test_build_and_validate_recon_item():
    from recon.recon_item import build_recon_item, validate_recon_item
    item = build_recon_item(
        "huntr-acme", {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"},
        AssetMetadata("acme", "npm", latest="4.2.1", repo_url="github.com/acme-org/acme"),
        _closure(),
        CloneResult(cloned=True, clone_path="runtime/recon/huntr-acme/source/acme-org-acme",
                    commit_sha="abc"),
        [Advisory("GHSA-x", "CVE-2024-1", "osv", "7.5", "<4.2.0", "4.2.0", "acme")],
        extra_flags=[], ts="2026-06-21T00:00:00Z")
    ok, errors = validate_recon_item(item)
    assert ok, errors
    assert item["resolved_version"] == "4.2.1"
    assert item["repo"]["cloned"] is True
    assert item["transitive_closure"]["count"] == 1
    assert item["known_advisories"][0]["id"] == "GHSA-x"


def test_flags_propagate_from_closure_and_clone():
    from recon.recon_item import build_recon_item
    c = Closure(no_lockfile=True)
    item = build_recon_item(
        "s", {"asset_type": "package", "identifier": "x", "ecosystem": "npm"},
        None, c,
        CloneResult(cloned=False, skipped_reason="size>500MB cap"),
        [], extra_flags=["advisory_source_error:osv"], ts="2026-06-21T00:00:00Z")
    assert "no_lockfile" in item["flags"]
    assert any(f.startswith("clone_skipped") for f in item["flags"])
    assert "advisory_source_error:osv" in item["flags"]


def test_write_program_recon_emits_json_and_closure(tmp_path):
    from recon.recon_item import build_recon_item, write_program_recon
    item = build_recon_item("s", {"asset_type": "package", "identifier": "x", "ecosystem": "npm"},
                            None, _closure(), None, [], extra_flags=[], ts="2026-06-21T00:00:00Z")
    out = write_program_recon("s", [item], {"x": _closure()}, tmp_path)
    assert (tmp_path / "s" / "recon.json").exists()
    assert (tmp_path / "s" / "dep-graph" / "x.closure.jsonl").exists()
    assert out == tmp_path / "s" / "recon.json"
