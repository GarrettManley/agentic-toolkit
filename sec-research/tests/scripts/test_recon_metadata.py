import json
from pathlib import Path

FX = Path(__file__).resolve().parent.parent / "fixtures" / "recon"


def _write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def test_npm_metadata_parses_repo_and_versions(tmp_path):
    from recon.metadata import fetch_metadata
    fx = tmp_path / "npm.json"
    _write(fx, {
        "dist-tags": {"latest": "4.2.1"},
        "versions": {"4.2.0": {}, "4.2.1": {}},
        "repository": {"url": "git+https://github.com/acme-org/acme.git"},
        "maintainers": [{"name": "alice"}, {"name": "bob"}],
    })
    m = fetch_metadata("acme", "npm", from_fixture=fx)
    assert m.latest == "4.2.1"
    assert set(m.versions) == {"4.2.0", "4.2.1"}
    assert m.repo_url == "github.com/acme-org/acme"
    assert m.maintainers == ["alice", "bob"]


def test_pypi_metadata_parses(tmp_path):
    from recon.metadata import fetch_metadata
    fx = tmp_path / "pypi.json"
    _write(fx, {
        "info": {"version": "2.31.0",
                 "project_urls": {"Source": "https://github.com/psf/requests"}},
        "releases": {"2.30.0": [], "2.31.0": []},
    })
    m = fetch_metadata("requests", "pypi", from_fixture=fx)
    assert m.latest == "2.31.0"
    assert m.repo_url == "github.com/psf/requests"
    assert set(m.versions) == {"2.30.0", "2.31.0"}


def test_metadata_missing_repo_is_none(tmp_path):
    from recon.metadata import fetch_metadata
    fx = tmp_path / "npm.json"
    _write(fx, {"dist-tags": {"latest": "1.0.0"}, "versions": {"1.0.0": {}}})
    m = fetch_metadata("noredir", "npm", from_fixture=fx)
    assert m.repo_url is None and m.latest == "1.0.0"
