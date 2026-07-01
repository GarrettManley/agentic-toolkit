import json
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


def test_validate_recon_item_rejects_invalid():
    from recon.recon_item import validate_recon_item
    ok, errors = validate_recon_item({"slug": 123})
    assert ok is False
    assert len(errors) > 0


def test_flags_closure_truncated():
    from recon.recon_item import build_recon_item
    c = Closure(direct=[Dep("lodash", "4.17.21", "npm")],
                deps=[Dep("lodash", "4.17.21", "npm")],
                lockfile="package-lock.json", no_lockfile=False,
                truncated=True, total_before_cap=5)
    item = build_recon_item(
        "s", {"asset_type": "package", "identifier": "x", "ecosystem": "npm"},
        None, c, None, [], extra_flags=[], ts="2026-06-21T00:00:00Z")
    assert "closure_truncated" in item["flags"]


def test_write_program_recon_emits_json_and_closure(tmp_path):
    from recon.recon_item import build_recon_item, write_program_recon
    item = build_recon_item("s", {"asset_type": "package", "identifier": "x", "ecosystem": "npm"},
                            None, _closure(), None, [], extra_flags=[], ts="2026-06-21T00:00:00Z")
    out = write_program_recon("s", [item], {"x": _closure()}, tmp_path)
    assert (tmp_path / "s" / "recon.json").exists()
    assert (tmp_path / "s" / "dep-graph" / "x.closure.jsonl").exists()
    assert out == tmp_path / "s" / "recon.json"
    written_items = json.loads((tmp_path / "s" / "recon.json").read_text(encoding="utf-8"))
    assert len(written_items) == 1
    assert written_items[0]["slug"] == "s"
    assert written_items[0]["asset"]["identifier"] == "x"
    closure_lines = (tmp_path / "s" / "dep-graph" / "x.closure.jsonl").read_text(
        encoding="utf-8").splitlines()
    assert len(closure_lines) >= 1
    dep = json.loads(closure_lines[0])
    assert dep["name"] == "lodash"


def test_write_program_recon_handles_repo_asset_id_with_slashes(tmp_path):
    """Regression (caught in first live GHSA run): a repo asset id like
    'github.com/isaacs/minimatch' must flatten to a single closure file, not create
    unintended nested dirs (which crashed write_text with FileNotFoundError)."""
    from recon.recon_item import build_recon_item, write_program_recon, _safe_asset_filename
    asset_id = "github.com/isaacs/minimatch"
    item = build_recon_item(
        "ghsa-isaacs-minimatch",
        {"asset_type": "repo", "identifier": asset_id, "ecosystem": None},
        None, _closure(), None, [], extra_flags=[], ts="2026-06-27T00:00:00Z")
    out = write_program_recon("ghsa-isaacs-minimatch", [item], {asset_id: _closure()}, tmp_path)
    assert out.exists()
    expected = tmp_path / "ghsa-isaacs-minimatch" / "dep-graph" / "github.com__isaacs__minimatch.closure.jsonl"
    assert expected.exists()
    # The recorded path in recon.json must match the file actually written.
    assert item["transitive_closure"]["path"].endswith(_safe_asset_filename(asset_id) + ".closure.jsonl")


def test_build_recon_item_repo_identifier_falls_back_when_no_metadata():
    """Pre-existing gap (found via review of the hb-7hf plan, not introduced by it):
    repo.identifier was None for any repo-type asset, since metadata is only ever
    fetched for package-type assets. repo_identifier lets the caller supply the real
    clone-driving identifier explicitly."""
    from recon.recon_item import build_recon_item
    from recon.clone import CloneResult
    item = build_recon_item(
        "ghsa-isaacs-minimatch",
        {"asset_type": "repo", "identifier": "github.com/isaacs/minimatch", "ecosystem": None},
        None, _closure(),
        CloneResult(cloned=True, clone_path="runtime/recon/ghsa-isaacs-minimatch/source/x", commit_sha="abc"),
        [], extra_flags=[], ts="2026-07-01T00:00:00Z",
        repo_identifier="github.com/isaacs/minimatch")
    assert item["repo"]["identifier"] == "github.com/isaacs/minimatch"


def test_build_recon_item_repo_identifier_defaults_to_metadata_when_omitted():
    """Backward-compat: omitting repo_identifier preserves today's behavior exactly."""
    from recon.recon_item import build_recon_item
    from recon.metadata import AssetMetadata
    from recon.clone import CloneResult
    item = build_recon_item(
        "huntr-acme", {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"},
        AssetMetadata("acme", "npm", latest="4.2.1", repo_url="github.com/acme-org/acme"),
        _closure(),
        CloneResult(cloned=True, clone_path="runtime/recon/huntr-acme/source/acme-org-acme", commit_sha="abc"),
        [], extra_flags=[], ts="2026-06-21T00:00:00Z")
    assert item["repo"]["identifier"] == "github.com/acme-org/acme"
