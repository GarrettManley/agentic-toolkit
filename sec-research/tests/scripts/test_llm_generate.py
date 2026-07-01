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
    # tmp_programs is the existing conftest fixture; write a scope that includes lodash and left-pad.
    import yaml
    from lib import scope_match
    slug_dir = tmp_programs / "huntr-acme"
    slug_dir.mkdir()
    (slug_dir / "scope.yaml").write_text(yaml.safe_dump({
        "program_slug": "huntr-acme", "venue": "huntr",
        "in_scope": [
            {"asset_type": "package", "identifier": "lodash", "ecosystem": "npm"},
            {"asset_type": "package", "identifier": "left-pad", "ecosystem": "npm"},
            {"asset_type": "package", "identifier": "minimatch", "ecosystem": "npm"},
        ],
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
    assert out == []  # target (evil-pkg) is neither the recon asset nor in scope -> hard drop


def test_generate_drops_target_diverging_from_recon_asset(scoped, tmp_path):
    """A dependency-cve hypothesis whose target.identifier differs from the recon item's asset is
    dropped (hypothesis-target-divergence) even when that target is independently IN SCOPE — the
    finding must be filed under the asset the recon-stamped seed/PoC actually tests, not a sibling.
    left-pad is in the scope fixture, so the old same-slug scope gate would NOT have caught this."""
    from llm.generate import generate_hypotheses
    client = FakeClient([{"hypotheses": [_model_hypothesis(identifier="left-pad")]}])
    out = generate_hypotheses(scoped, [_recon_item()], client=client,  # recon item is lodash
                              hyp_root=tmp_path, now=NOW)
    assert out == []


def test_generate_empty_playbooks_is_noop(scoped, tmp_path):
    from llm.generate import generate_hypotheses
    client = FakeClient([{"hypotheses": [_model_hypothesis()]}])
    out = generate_hypotheses(scoped, [_recon_item()], client=client,
                              playbooks_root=tmp_path / "empty", hyp_root=tmp_path, now=NOW)
    assert out == []
    assert client.calls == 0  # never prompted the model


def test_generate_isolates_asset_on_llm_unavailable(scoped, tmp_path):
    from llm.generate import generate_hypotheses
    # item2 targets a DISTINCT package (left-pad) so dedup cannot explain len==1 —
    # only true per-asset isolation of the LLMUnavailable failure can.
    item2 = {
        "slug": "huntr-acme",
        "asset": {"asset_type": "package", "identifier": "left-pad", "ecosystem": "npm"},
        "resolved_version": "1.0.0", "recon_ts": "2026-06-22T08:00:00Z",
        "known_advisories": [{"id": "GHSA-y", "cve": "CVE-2020-0001",
                               "affected_range": "<1.0.1", "fixed": "1.0.1",
                               "package": "left-pad"}],
    }
    client = FakeClient([
        LLMUnavailable("down"),                              # item1 (lodash) fails
        {"hypotheses": [_model_hypothesis(identifier="left-pad")]},  # item2 (left-pad) succeeds
    ])
    out = generate_hypotheses(scoped, [_recon_item(), item2], client=client,
                              hyp_root=tmp_path, now=NOW)
    assert len(out) == 1  # first asset failed, second succeeded
    assert out[0]["target"]["identifier"] == "left-pad"  # proves it's item2's hypothesis


def test_generate_drops_invalid_hypothesis(scoped, tmp_path):
    """Hypotheses that fail validate_hypothesis (e.g. missing required field) are dropped."""
    from llm.generate import generate_hypotheses
    # Omit required "signals_matched" field — schema validation must reject this.
    bad_hypothesis = {k: v for k, v in _model_hypothesis().items() if k != "signals_matched"}
    client = FakeClient([{"hypotheses": [bad_hypothesis]}])
    out = generate_hypotheses(scoped, [_recon_item()], client=client,
                              hyp_root=tmp_path, now=NOW)
    assert out == []       # bad hypothesis was dropped post-validation
    assert client.calls == 1  # the model WAS called — drop happens after the call


def test_generate_dedupes_identical_hypotheses(scoped, tmp_path):
    """A response containing two identical hypotheses (same identifier/vuln_class/technique) yields one."""
    from llm.generate import generate_hypotheses
    h = _model_hypothesis()
    client = FakeClient([{"hypotheses": [h, h]}])  # same dict twice in one response
    out = generate_hypotheses(scoped, [_recon_item()], client=client,
                              hyp_root=tmp_path, now=NOW)
    assert len(out) == 1


def test_generate_drops_unparseable_response(scoped, tmp_path):
    """A response whose text is not valid JSON is silently dropped (parse-error branch)."""
    from llm.generate import generate_hypotheses

    class FakeClientRawText:
        provider = "fake"
        calls = 0
        def complete_json(self, **kw):
            self.calls += 1
            from llm.client import ChatResponse
            return ChatResponse(text="NOT JSON", provider="fake", model="m",
                                finish_reason="stop", usage=None)

    client = FakeClientRawText()
    out = generate_hypotheses(scoped, [_recon_item()], client=client,
                              hyp_root=tmp_path, now=NOW)
    assert out == []


def test_generate_drops_dependency_cve_with_unresolved_version(scoped, tmp_path):
    """When recon cannot supply resolved_version, a dependency-cve PoC has no install target, so
    the hypothesis is dropped with a hypothesis-version-unresolved trace, not persisted PoC-dead."""
    from llm.generate import generate_hypotheses
    item = {k: v for k, v in _recon_item().items() if k != "resolved_version"}
    client = FakeClient([{"hypotheses": [_model_hypothesis()]}])
    out = generate_hypotheses(scoped, [item], client=client, hyp_root=tmp_path, now=NOW)
    assert out == []


def test_generate_stamps_package_name_from_relabeled_ghsa_asset(scoped, tmp_path):
    """hb-7hf regression: a GHSA-sourced recon item relabeled by recon_program.py's fix
    (asset_type='package', identifier=<npm pkg name>, ecosystem='npm') must have
    _normalize_authored's package_name stamp read from asset['identifier'] ('minimatch'),
    not any model-authored value — proving the fix reaches the generate.py boundary
    _stamp_or_drop reads, not just select_playbooks. The model hypothesis below is
    authored (via _model_hypothesis) with evidence_seed.package_name='lodash' — the
    server-stamp must overwrite it with the recon asset's true identifier."""
    from llm.generate import generate_hypotheses
    item = {
        "slug": "huntr-acme",
        "asset": {"asset_type": "package", "identifier": "minimatch", "ecosystem": "npm"},
        "resolved_version": "3.0.4", "recon_ts": "2026-06-22T08:00:00Z",
        "known_advisories": [{"id": "GHSA-x", "cve": "CVE-2022-3517",
                              "affected_range": "<3.0.5", "fixed": "3.0.5",
                              "package": "minimatch"}],
    }
    client = FakeClient([{"hypotheses": [_model_hypothesis(identifier="minimatch")]}])
    out = generate_hypotheses(scoped, [item], client=client, hyp_root=tmp_path, now=NOW)
    assert len(out) == 1
    assert out[0]["evidence_seed"]["package_name"] == "minimatch"
