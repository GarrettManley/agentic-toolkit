from __future__ import annotations

from llm.generate import _advisory_fixed_version


def test_advisory_fixed_version_matches_cve():
    item = {"known_advisories": [
        {"cve": "CVE-2019-10744", "fixed": "4.17.12", "package": "lodash"},
        {"cve": "CVE-2020-0001", "fixed": "9.9.9", "package": "other"},
    ]}
    assert _advisory_fixed_version(item, "CVE-2019-10744") == "4.17.12"


def test_advisory_fixed_version_none_when_no_match():
    item = {"known_advisories": [{"cve": "CVE-2020-0001", "fixed": "9.9.9"}]}
    assert _advisory_fixed_version(item, "CVE-2019-10744") is None


def test_advisory_fixed_version_handles_missing_advisories():
    assert _advisory_fixed_version({}, "CVE-2019-10744") is None
    assert _advisory_fixed_version({"known_advisories": []}, None) is None
