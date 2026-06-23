import pytest
from scripts.draft.registry import (select_finding_template, FINDING_TEMPLATE_REGISTRY,
                                     IncompleteVerdict, ecosystem_of)
from scripts.draft.llm_template import LLMFindingTemplate
from scripts.verify.model import Verdict, VERDICT_VERIFIED

def _v(**kw):
    base = dict(hypothesis_id="h", program_slug="p", target_identifier="minimatch@3.0.4",
                vuln_class="dependency-cve", verdict=VERDICT_VERIFIED, reason="ok",
                strategy="templated", template_id="npm:minimatch:CVE-2022-3517",
                evidence=[], verified_at="t")
    base.update(kw); return Verdict(**base)

def test_registry_has_npm_dependency_cve():
    assert ("dependency-cve", "npm") in FINDING_TEMPLATE_REGISTRY
    assert select_finding_template("dependency-cve", "npm") is not None

def test_unregistered_returns_none():
    assert select_finding_template("dependency-cve", "cargo") is None

def test_ecosystem_parsed_from_template_id():
    assert ecosystem_of(_v()) == "npm"

def test_incomplete_verdict_reexported_from_registry():
    # same class object as the one in errors.py (re-export, not a redefinition)
    from scripts.draft.errors import IncompleteVerdict as ErrIV
    assert IncompleteVerdict is ErrIV

def test_llm_seam_is_closed():
    seam = LLMFindingTemplate()
    assert seam.supports(_v()) is False
    with pytest.raises(NotImplementedError):
        seam.build(_v(), [])
