from __future__ import annotations
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parents[2] / "schema" / "hypothesis.schema.json"


def _valid_hypothesis() -> dict:
    return {
        "hypothesis_id": "HYP-2026-06-22-001",
        "program_slug": "huntr-acme",
        "target": {"asset_type": "package", "identifier": "lodash",
                   "version_or_revision": "4.17.20", "ecosystem": "npm"},
        "vuln_class": "dependency-cve",
        "source_playbook": {"vuln_class": "dependency-cve",
                            "technique": "known-advisory-confirmation",
                            "playbook_trace_id": "trace-pb-2026-06-22-001"},
        "rationale": "Recon found OSV advisory GHSA-xxxx affecting <4.17.21; resolved version 4.17.20 is in range.",
        "confidence": 0.7,
        "signals_matched": ["known_advisory present", "resolved_version in affected_range"],
        "evidence_seed": {"package_ecosystem": "npm", "package_name": "lodash",
                          "affected_versions_range": "<4.17.21",
                          "candidate_cve_id": "CVE-2021-23337",
                          "attack_vector_hypothesis": "prototype pollution via zipObjectDeep"},
        "advisory_refs": ["GHSA-xxxx", "CVE-2021-23337"],
        "recon_ref": {"slug": "huntr-acme", "asset_identifier": "lodash",
                      "recon_ts": "2026-06-22T08:00:00Z"},
        "generated_at": "2026-06-22T08:05:00Z",
        "generator": {"provider": "claude", "model": "claude-sonnet-4-6"},
    }


def test_schema_is_valid_jsonschema():
    data = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert data["$schema"].startswith("https://json-schema.org/draft/")
    Draft202012Validator.check_schema(data)


def test_valid_hypothesis_passes():
    from llm.schema import validate_hypothesis
    ok, errors = validate_hypothesis(_valid_hypothesis())
    assert ok, errors


def test_short_rationale_fails():
    from llm.schema import validate_hypothesis
    bad = _valid_hypothesis() | {"rationale": "too short"}
    ok, errors = validate_hypothesis(bad)
    assert not ok


def test_out_of_enum_vuln_class_fails():
    from llm.schema import validate_hypothesis
    bad = _valid_hypothesis() | {"vuln_class": "not-a-class"}
    ok, _ = validate_hypothesis(bad)
    assert not ok


def test_model_item_schema_strips_server_fields():
    from llm.schema import load_schema, model_item_schema, SERVER_FIELDS
    item = model_item_schema(load_schema())
    for f in SERVER_FIELDS:
        assert f not in item["properties"]
        assert f not in item.get("required", [])
    assert item["additionalProperties"] is False


def test_wrapper_schema_is_array_of_items():
    from llm.schema import load_schema, wrapper_schema
    w = wrapper_schema(load_schema())
    assert w["properties"]["hypotheses"]["type"] == "array"
    assert w["required"] == ["hypotheses"]
