from scripts.triage.dedup import extract_cve, match_advisories, triage_verdicts
from scripts.triage.model import TRIAGE_NOVEL, TRIAGE_DUPLICATE
from scripts.verify.model import Verdict, VERDICT_VERIFIED, VERDICT_REFUTED
from scripts.recon.advisories import Advisory

NOW = "2026-06-22T00:00:00Z"

def _v(**kw):
    base = dict(hypothesis_id="h1", program_slug="p", target_identifier="minimatch@3.0.4",
                vuln_class="dependency-cve", verdict=VERDICT_VERIFIED, reason="ok",
                strategy="templated", template_id="npm:minimatch:CVE-2022-3517",
                evidence=[], verified_at=NOW)
    base.update(kw); return Verdict(**base)

def _adv(**kw):
    base = dict(id="GHSA-f8q6-p94x-37v3", cve="CVE-2022-3517", source="osv",
                severity="7.5", affected_range="<3.0.5", fixed="3.0.5", package="minimatch")
    base.update(kw); return Advisory(**base)

def test_extract_cve_from_template_id():
    assert extract_cve(_v()) == "CVE-2022-3517"

def test_extract_cve_none_when_absent():
    assert extract_cve(_v(template_id=None, reason="redos")) is None

def test_known_cve_is_duplicate():
    hits = match_advisories(_v(), [_adv()])
    assert "CVE-2022-3517" in hits or "GHSA-f8q6-p94x-37v3" in hits

def test_no_cve_verdict_is_novel():
    assert match_advisories(_v(template_id=None, reason="redos"), [_adv()]) == []

def test_triage_filters_non_verified_and_classifies():
    verdicts = [_v(), _v(verdict=VERDICT_REFUTED), _v(template_id="npm:left-pad:CVE-2099-0001")]
    results = triage_verdicts(verdicts, [_adv()], now=NOW)
    assert len(results) == 2  # refuted dropped
    by_target = {r.verdict.template_id: r for r in results}
    assert by_target["npm:minimatch:CVE-2022-3517"].triage_status == TRIAGE_DUPLICATE
    assert by_target["npm:left-pad:CVE-2099-0001"].triage_status == TRIAGE_NOVEL
    assert by_target["npm:left-pad:CVE-2099-0001"].dedup.checked_against  # advisories were consulted
