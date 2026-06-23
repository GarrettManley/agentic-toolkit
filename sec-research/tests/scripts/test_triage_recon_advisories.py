"""Tests for scripts/triage/recon_advisories.py — load_advisories adapter.

Fixture shape mirrors scripts/recon/recon_item.write_program_recon output:
  runtime/recon/<slug>/recon.json → a JSON *list* of recon-item dicts.
Each item carries "asset": {"identifier": ...} and
"known_advisories": [asdict(Advisory)].
"""
import json
from pathlib import Path

from scripts.triage.recon_advisories import load_advisories


def _recon_item(identifier: str, advisories: list[dict]) -> dict:
    """Minimal recon item matching recon_item.build_recon_item output."""
    return {
        "slug": "huntr-npm-minimatch",
        "asset": {"asset_type": "package", "identifier": identifier, "ecosystem": "npm"},
        "resolved_version": "3.0.4",
        "repo": None,
        "direct_deps": [],
        "transitive_closure": {"count": 0, "truncated": False, "path": None},
        "known_advisories": advisories,
        "flags": [],
        "recon_ts": "2026-06-22T00:00:00Z",
    }


def test_load_advisories_from_recon_output(tmp_path: Path):
    slug = "huntr-npm-minimatch"
    recon_dir = tmp_path / "recon" / slug
    recon_dir.mkdir(parents=True)
    advisory = {
        "id": "GHSA-f8q6-p94x-37v3",
        "cve": "CVE-2022-3517",
        "source": "osv",
        "severity": "7.5",
        "affected_range": "<3.0.5",
        "fixed": "3.0.5",
        "package": "minimatch",
    }
    items = [_recon_item("minimatch@3.0.4", [advisory])]
    (recon_dir / "recon.json").write_text(json.dumps(items), encoding="utf-8")

    advs = load_advisories(slug, runtime_root=tmp_path)
    assert len(advs) == 1
    assert advs[0].cve == "CVE-2022-3517"
    assert advs[0].id == "GHSA-f8q6-p94x-37v3"
    assert advs[0].package == "minimatch"
    assert advs[0].source == "osv"


def test_load_advisories_multiple_assets(tmp_path: Path):
    """Advisories across multiple recon items are all collected."""
    slug = "huntr-npm-foo"
    recon_dir = tmp_path / "recon" / slug
    recon_dir.mkdir(parents=True)
    adv1 = {"id": "GHSA-aaa", "cve": "CVE-2022-0001", "source": "osv",
             "severity": "5.0", "affected_range": "<1.0.1", "fixed": "1.0.1", "package": "foo"}
    adv2 = {"id": "GHSA-bbb", "cve": None, "source": "disclosed",
             "severity": None, "affected_range": None, "fixed": None, "package": "bar"}
    items = [
        _recon_item("foo@1.0.0", [adv1]),
        _recon_item("bar@2.0.0", [adv2]),
    ]
    (recon_dir / "recon.json").write_text(json.dumps(items), encoding="utf-8")

    advs = load_advisories(slug, runtime_root=tmp_path)
    assert len(advs) == 2
    ids = {a.id for a in advs}
    assert ids == {"GHSA-aaa", "GHSA-bbb"}


def test_load_advisories_missing_recon_returns_empty(tmp_path: Path):
    assert load_advisories("no-such-slug", runtime_root=tmp_path) == []


def test_load_advisories_item_with_no_advisories(tmp_path: Path):
    slug = "huntr-npm-empty"
    recon_dir = tmp_path / "recon" / slug
    recon_dir.mkdir(parents=True)
    items = [_recon_item("pkg@1.0.0", [])]
    (recon_dir / "recon.json").write_text(json.dumps(items), encoding="utf-8")

    advs = load_advisories(slug, runtime_root=tmp_path)
    assert advs == []
