import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
from llm.generate import _normalize_authored  # noqa: E402

ITEM = {
    "slug": "huntr-npm-minimatch",
    "asset": {"asset_type": "package", "identifier": "minimatch", "ecosystem": "npm"},
    "resolved_version": "3.0.4",
}


def _h(target, seed, vuln_class="dependency-cve"):
    return {"vuln_class": vuln_class, "target": dict(target), "evidence_seed": dict(seed)}


def test_cve_id_aliases_map_to_candidate():
    for key in ("cve_id", "cve_id_proposed_or_assigned"):
        h = _h({"identifier": "minimatch"}, {key: "CVE-2022-3517"})
        _normalize_authored(h, ITEM)
        assert h["evidence_seed"]["candidate_cve_id"] == "CVE-2022-3517"


def test_recon_overwrites_package_identity():
    # model supplies WRONG ecosystem/name -> recon ground truth wins (feeds npm install + scope)
    h = _h(
        {"identifier": "minimatch"},
        {"candidate_cve_id": "CVE-2022-3517", "package_ecosystem": "pypi", "package_name": "evil"},
    )
    _normalize_authored(h, ITEM)
    s = h["evidence_seed"]
    assert s["package_ecosystem"] == "npm" and s["package_name"] == "minimatch"


def test_backfills_package_identity_when_seed_omits_it():
    h = _h({"identifier": "minimatch", "ecosystem": "npm"}, {"candidate_cve_id": "CVE-2022-3517"})
    _normalize_authored(h, ITEM)
    s = h["evidence_seed"]
    assert s["package_ecosystem"] == "npm" and s["package_name"] == "minimatch"


def test_stamps_target_version_from_recon():
    h = _h({"identifier": "minimatch"}, {"candidate_cve_id": "CVE-2022-3517"})
    _normalize_authored(h, ITEM)
    assert h["target"]["version_or_revision"] == "3.0.4"


def test_drops_model_version_when_recon_absent():
    h = _h({"identifier": "minimatch", "version_or_revision": "9.9.9"}, {"candidate_cve_id": "x"})
    _normalize_authored(h, {"asset": {"identifier": "minimatch", "ecosystem": "npm"}})  # no resolved_version
    assert "version_or_revision" not in h["target"]  # model-authored install target dropped


def test_preserves_model_candidate_cve_id():
    h = _h({"identifier": "minimatch"}, {"candidate_cve_id": "CVE-2022-3517"})
    _normalize_authored(h, ITEM)
    assert h["evidence_seed"]["candidate_cve_id"] == "CVE-2022-3517"


def test_non_dependency_cve_left_untouched():
    h = _h({"identifier": "x"}, {"candidate_cve_id": "y"}, vuln_class="logic-flaw")
    _normalize_authored(h, ITEM)
    assert "package_ecosystem" not in h["evidence_seed"]
    assert "version_or_revision" not in h["target"]


def test_drops_package_name_when_recon_lacks_identifier():
    # recon asset without identifier -> a model package_name must NOT ride through to npm install
    h = _h({"identifier": "minimatch"}, {"candidate_cve_id": "x", "package_name": "evil"})
    _normalize_authored(h, {"asset": {"ecosystem": "npm"}, "resolved_version": "3.0.4"})
    assert "package_name" not in h["evidence_seed"]
