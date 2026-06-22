import json
from pathlib import Path

from recon.deps import Dep


def test_osv_batch_maps_to_advisories(tmp_path):
    from recon.advisories import correlate
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({"results": [
        {"vulns": [{"id": "GHSA-xxxx"}]},
        {},  # second dep: no vulns
    ]}), encoding="utf-8")
    detail = {
        "GHSA-xxxx": {
            "id": "GHSA-xxxx", "aliases": ["CVE-2024-1234"],
            "severity": [{"type": "CVSS_V3", "score": "7.5"}],
            "affected": [{"package": {"name": "acme"},
                          "ranges": [{"events": [{"introduced": "0"}, {"fixed": "4.2.0"}]}]}],
        }
    }
    deps = [Dep("acme", "4.1.0", "npm"), Dep("ms", "2.1.3", "npm")]
    advs, errors = correlate(deps, tmp_path / "disclosed",
                             osv_batch_fixture=batch, osv_detail_fixtures=detail)
    assert errors == []
    a = next(x for x in advs if x.id == "GHSA-xxxx")
    assert a.cve == "CVE-2024-1234" and a.source == "osv"
    assert a.severity == "7.5" and a.fixed == "4.2.0" and a.package == "acme"


def test_disclosed_reports_are_folded_in(tmp_path):
    from recon.advisories import correlate
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({"results": [{}]}), encoding="utf-8")
    disclosed = tmp_path / "disclosed"
    disclosed.mkdir()
    (disclosed / "GHSA-yyyy.json").write_text(
        json.dumps({"id": "GHSA-yyyy", "package": "acme", "severity": "low"}), encoding="utf-8")
    advs, errors = correlate([Dep("acme", "1.0.0", "npm")], disclosed,
                             osv_batch_fixture=batch, osv_detail_fixtures={})
    assert any(a.id == "GHSA-yyyy" and a.source == "disclosed" for a in advs)


def test_osv_source_error_is_flagged_not_fatal(tmp_path, monkeypatch):
    from recon import advisories as adv
    def boom(url, payload, **kw):
        raise adv._http.HttpError("osv down")
    monkeypatch.setattr(adv._http, "http_post_json", boom)
    advs, errors = adv.correlate([Dep("acme", "1.0.0", "npm")], tmp_path / "disclosed")
    assert advs == [] and any("osv" in e for e in errors)
