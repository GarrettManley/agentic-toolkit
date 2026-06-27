"""Tests for verify.llm_strategy.LLMPocStrategy — LLM-backed PoC authoring.

Offline: a fake LLMClient returns canned PoC JSON. No network.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from verify.llm_strategy import LLMPocStrategy
from verify.strategy import PocStrategy, PocPlan, SeedIncomplete
from llm.client import ChatResponse


class _FakeClient:
    provider = "fake"

    def __init__(self, payload: dict):
        self._payload = payload
        self.calls = []

    def complete_json(self, *, system, messages, schema, **kw) -> ChatResponse:
        self.calls.append({"system": system, "messages": messages})
        return ChatResponse(text=json.dumps(self._payload), provider="fake",
                            model="fake-1", finish_reason="stop", usage=None)


def _payload():
    return {
        "files": {
            "trigger.js": "/* authored */ process.stdout.write('VC\\n');",
            "package.json": '{"name":"poc","private":true}',
        },
        "trigger_cmd": ["node", "trigger.js"],
        "sentinel_confirmed": "VC",
        "expected_confirmed_exit": 0,
        "sentinel_patched": "PT",
        "expected_patched_exit": 1,
        "reasoning": "fires on affected only",
    }


def _hyp(fixed="4.17.12"):
    seed = {
        "package_ecosystem": "npm", "package_name": "lodash",
        "candidate_cve_id": "CVE-2019-10744", "affected_versions_range": "<4.17.12",
    }
    if fixed is not None:
        seed["fixed_version"] = fixed
    return {
        "hypothesis_id": "HYP-1", "program_slug": "huntr-npm-lodash",
        "vuln_class": "dependency-cve",
        "target": {"identifier": "lodash", "version_or_revision": "4.17.4"},
        "evidence_seed": seed,
    }


def test_satisfies_protocol():
    assert isinstance(LLMPocStrategy(), PocStrategy)


def test_name_and_repair_flag():
    s = LLMPocStrategy()
    assert s.name == "llm"
    assert s.supports_repair is True


def test_supports_true_for_npm_dependency_cve_with_fixed_version():
    assert LLMPocStrategy().supports(_hyp()) is True


def test_supports_false_without_fixed_version():
    assert LLMPocStrategy().supports(_hyp(fixed=None)) is False


def test_supports_false_for_non_npm():
    h = _hyp()
    h["evidence_seed"]["package_ecosystem"] = "pypi"
    assert LLMPocStrategy().supports(h) is False


def test_supports_false_for_wrong_vuln_class():
    h = _hyp()
    h["vuln_class"] = "auth-bypass"
    assert LLMPocStrategy().supports(h) is False


def test_supports_returns_bool():
    assert type(LLMPocStrategy().supports({})) is bool


def test_build_plan_materializes_differential_plan():
    client = _FakeClient(_payload())
    plan = LLMPocStrategy(client=client).build_plan(_hyp())
    assert isinstance(plan, PocPlan)
    assert plan.is_differential is True
    assert plan.install_cmd == ["npm", "install", "--no-save", "lodash@4.17.4"]
    assert plan.fixed_install_cmd == ["npm", "install", "--no-save", "lodash@4.17.12"]
    assert plan.expected_trigger_exit == 0
    assert plan.expected_refuted_exit == 1
    assert plan.expected_trigger_sha256 == hashlib.sha256(b"VC\n").hexdigest()
    assert plan.expected_refuted_sha256 == hashlib.sha256(b"PT\n").hexdigest()
    assert plan.trigger_cmd == ["node", "trigger.js"]
    assert "trigger.js" in plan.files


def test_build_plan_injects_default_package_json_if_absent():
    payload = _payload()
    del payload["files"]["package.json"]
    plan = LLMPocStrategy(client=_FakeClient(payload)).build_plan(_hyp())
    assert "package.json" in plan.files


def test_build_plan_raises_seed_incomplete_without_fixed_version():
    with pytest.raises(SeedIncomplete):
        LLMPocStrategy(client=_FakeClient(_payload())).build_plan(_hyp(fixed=None))


def test_build_plan_passes_repair_context_into_prompt():
    client = _FakeClient(_payload())
    LLMPocStrategy(client=client).build_plan(_hyp(), repair_context={"issue": "no-discrimination"})
    assert "no-discrimination" in client.calls[-1]["messages"][0]["content"]
