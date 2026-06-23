"""Tests for scripts/triage/model.py — TriageResult, DedupInfo, triage constants."""
from dataclasses import FrozenInstanceError
import pytest
from scripts.triage.model import TriageResult, DedupInfo, TRIAGE_NOVEL, TRIAGE_DUPLICATE
from scripts.verify.model import Verdict, VERDICT_VERIFIED

def _verdict(**kw):
    base = dict(hypothesis_id="h1", program_slug="huntr-npm-minimatch",
                target_identifier="minimatch@3.0.4", vuln_class="dependency-cve",
                verdict=VERDICT_VERIFIED, reason="ok", strategy="templated",
                template_id="npm:minimatch:CVE-2022-3517", evidence=[],
                verified_at="2026-06-22T00:00:00Z")
    base.update(kw); return Verdict(**base)

def test_dedupinfo_fields_and_frozen():
    d = DedupInfo(checked_against=["CVE-2022-3517"], duplicates_found=["CVE-2022-3517"],
                  checked_at="2026-06-22T00:00:00Z", source="recon-osv")
    assert d.duplicates_found == ["CVE-2022-3517"]
    with pytest.raises(FrozenInstanceError):
        d.source = "x"

def test_triageresult_carries_verdict_and_status():
    d = DedupInfo(checked_against=[], duplicates_found=[], checked_at="t", source="recon-osv")
    r = TriageResult(verdict=_verdict(), is_novel=True, dedup=d, triage_status=TRIAGE_NOVEL)
    assert r.is_novel and r.triage_status == "novel"
    assert TRIAGE_DUPLICATE == "duplicate"
