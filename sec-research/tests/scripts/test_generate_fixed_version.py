from __future__ import annotations

from llm.generate import _advisory_fixed_version, _normalize_seed_keys, _resolve_fixed_version


def test_normalize_seed_maps_finding_vocab_to_hypothesis_keys():
    """Models often emit finding-schema field names (per the playbook's evidence
    template); normalize them onto the canonical hypothesis evidence_seed keys so
    _resolve_fixed_version can find the CVE. Caught live: gemma/qwen emitted
    cve_id_proposed_or_assigned, leaving candidate_cve_id absent -> un-verifiable."""
    seed = {"package_name": "minimatch",
            "cve_id_proposed_or_assigned": "CVE-2026-41907",
            "attack_vector": "RCE via untrusted input"}
    _normalize_seed_keys(seed)
    assert seed["candidate_cve_id"] == "CVE-2026-41907"
    assert seed["attack_vector_hypothesis"] == "RCE via untrusted input"
    assert "cve_id_proposed_or_assigned" not in seed
    assert "attack_vector" not in seed


def test_normalize_seed_does_not_clobber_canonical():
    """If the model already used the canonical key, the alias must not overwrite it."""
    seed = {"candidate_cve_id": "CVE-1", "cve_id_proposed_or_assigned": "CVE-2"}
    _normalize_seed_keys(seed)
    assert seed["candidate_cve_id"] == "CVE-1"


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


def test_resolve_overwrites_llm_supplied_fixed_version():
    """Advisory match MUST overwrite any LLM-supplied fixed_version (trust boundary).

    The LLM is an untrusted source for version pins; only the recon advisory is
    authoritative.  _resolve_fixed_version (called by generate_hypotheses after
    validate_hypothesis) enforces this by always setting fixed_version from the
    advisory, regardless of what the model wrote into evidence_seed."""
    item = {"known_advisories": [
        {"cve": "CVE-2019-10744", "fixed": "4.17.12", "package": "lodash"},
    ]}
    # Simulate an LLM-supplied pin that differs from the advisory value.
    seed = {"candidate_cve_id": "CVE-2019-10744", "fixed_version": "0.0.0-llm-supplied"}
    _resolve_fixed_version(item, seed)
    assert seed["fixed_version"] == "4.17.12"  # advisory value wins (overwrites LLM)


def test_resolve_drops_fixed_version_without_trusted_source():
    """No advisory match -> LLM-supplied fixed_version is DROPPED, not preserved.

    If the recon advisory has no match for the candidate CVE, there is no trusted
    version boundary.  _resolve_fixed_version pops any LLM-supplied value so it
    can never propagate to the differential install step."""
    item = {"known_advisories": []}  # no matching advisory
    seed = {"candidate_cve_id": "CVE-2099-99999", "fixed_version": "9.9.9-llm-supplied"}
    _resolve_fixed_version(item, seed)
    assert "fixed_version" not in seed  # dropped: no trusted source
