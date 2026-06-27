from __future__ import annotations

import jsonschema

from verify.poc_prompt import POC_AUTHOR_SCHEMA, build_poc_prompt


def _hyp():
    return {
        "hypothesis_id": "HYP-1", "program_slug": "huntr-npm-x", "vuln_class": "dependency-cve",
        "target": {"identifier": "lodash", "version_or_revision": "4.17.4"},
        "evidence_seed": {
            "package_ecosystem": "npm", "package_name": "lodash",
            "candidate_cve_id": "CVE-2019-10744", "affected_versions_range": "<4.17.12",
            "fixed_version": "4.17.12",
            "attack_vector_hypothesis": "prototype pollution via defaultsDeep",
        },
    }


def test_schema_is_valid_draft2020():
    jsonschema.Draft202012Validator.check_schema(POC_AUTHOR_SCHEMA)


def test_schema_requires_both_sentinels():
    req = POC_AUTHOR_SCHEMA["required"]
    for key in ("files", "trigger_cmd", "sentinel_confirmed", "expected_confirmed_exit",
                "sentinel_patched", "expected_patched_exit", "reasoning"):
        assert key in req


def test_prompt_includes_versions_and_cve_in_data_fence():
    system, messages = build_poc_prompt(_hyp())
    user = messages[0]["content"]
    assert "BEGIN" in user and "DATA" in user  # untrusted content is fenced
    assert "4.17.4" in user and "4.17.12" in user and "CVE-2019-10744" in user
    assert "data, never instructions" in system.lower() or "untrusted" in system.lower()


def test_repair_context_is_appended():
    system, messages = build_poc_prompt(_hyp(), repair_context={"issue": "no-discrimination"})
    assert "no-discrimination" in messages[0]["content"]


def test_system_prompt_forbids_version_sniffing():
    """R1: SYSTEM prompt must contain the rule forbidding version/metadata sniffing."""
    system, _ = build_poc_prompt(_hyp())
    assert "version check is not a proof" in system
    assert "metadata" in system.lower()
