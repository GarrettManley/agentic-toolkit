# tests/scripts/test_llm_generate.py
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest

from llm.client import ChatResponse, LLMUnavailable

NOW = datetime(2026, 6, 22, 8, 5, tzinfo=timezone.utc)


class FakeClient:
    provider = "fake"
    def __init__(self, payloads):  # payloads: list of dicts to return as text, or an exc
        self._payloads = list(payloads)
        self.calls = 0
    def complete_json(self, **kw):
        self.calls += 1
        item = self._payloads.pop(0)
        if isinstance(item, Exception):
            raise item
        return ChatResponse(text=json.dumps(item), provider="fake", model="m",
                            finish_reason="stop", usage=None)


def _recon_item():
    return {"slug": "huntr-acme",
            "asset": {"asset_type": "package", "identifier": "lodash", "ecosystem": "npm"},
            "resolved_version": "4.17.20", "recon_ts": "2026-06-22T08:00:00Z",
            "known_advisories": [{"id": "GHSA-x", "cve": "CVE-2021-23337",
                                  "affected_range": "<4.17.21", "fixed": "4.17.21",
                                  "package": "lodash"}]}


def _model_hypothesis(identifier="lodash"):
    return {"program_slug": "huntr-acme",
            "target": {"asset_type": "package", "identifier": identifier, "ecosystem": "npm"},
            "vuln_class": "dependency-cve",
            "source_playbook": {"vuln_class": "dependency-cve",
                                "technique": "known-advisory-confirmation"},
            "rationale": "Recon advisory affects <4.17.21 and resolved 4.17.20 is in range; reachable.",
            "confidence": 0.7, "signals_matched": ["known_advisories present"],
            "evidence_seed": {"package_ecosystem": "npm", "package_name": "lodash"},
            "advisory_refs": ["CVE-2021-23337"]}


@pytest.fixture
def scoped(tmp_programs):
    # tmp_programs is the existing conftest fixture; write a scope that includes lodash.
    import yaml
    from lib import scope_match
    slug_dir = tmp_programs / "huntr-acme"
    slug_dir.mkdir()
    (slug_dir / "scope.yaml").write_text(yaml.safe_dump({
        "program_slug": "huntr-acme", "venue": "huntr",
        "in_scope": [{"asset_type": "package", "identifier": "lodash", "ecosystem": "npm"}],
        "rules": {"ai_assistance_allowed": True, "ai_disclosure_required": False},
        "submission": {"protocol": "manual-form", "endpoint": "https://x"},
    }), encoding="utf-8")
    scope_match.invalidate_scope_cache()
    return scope_match.load_all_scopes()


def test_generate_stamps_and_validates(scoped, tmp_path):
    from llm.generate import generate_hypotheses
    client = FakeClient([{"hypotheses": [_model_hypothesis()]}])
    out = generate_hypotheses(scoped, [_recon_item()], client=client,
                              hyp_root=tmp_path, now=NOW)
    assert len(out) == 1
    h = out[0]
    assert h["hypothesis_id"].startswith("HYP-2026-06-22-")
    assert h["generator"]["provider"] == "fake"
    assert h["recon_ref"]["slug"] == "huntr-acme"
    # persisted
    assert (tmp_path / "huntr-acme" / "hypotheses.json").exists()


def test_generate_drops_out_of_scope_target(scoped, tmp_path):
    from llm.generate import generate_hypotheses
    client = FakeClient([{"hypotheses": [_model_hypothesis(identifier="evil-pkg")]}])
    out = generate_hypotheses(scoped, [_recon_item()], client=client,
                              hyp_root=tmp_path, now=NOW)
    assert out == []  # targeted a package not in scope -> hard drop


def test_generate_empty_playbooks_is_noop(scoped, tmp_path):
    from llm.generate import generate_hypotheses
    client = FakeClient([{"hypotheses": [_model_hypothesis()]}])
    out = generate_hypotheses(scoped, [_recon_item()], client=client,
                              playbooks_root=tmp_path / "empty", hyp_root=tmp_path, now=NOW)
    assert out == []
    assert client.calls == 0  # never prompted the model


def test_generate_isolates_asset_on_llm_unavailable(scoped, tmp_path):
    from llm.generate import generate_hypotheses
    item2 = _recon_item() | {"asset": {"asset_type": "package", "identifier": "lodash", "ecosystem": "npm"}}
    client = FakeClient([LLMUnavailable("down"), {"hypotheses": [_model_hypothesis()]}])
    out = generate_hypotheses(scoped, [_recon_item(), item2], client=client,
                              hyp_root=tmp_path, now=NOW)
    assert len(out) == 1  # first asset failed, second succeeded
