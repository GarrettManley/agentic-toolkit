"""Tests for scripts/draft/validate.py — Task 9: Finding self-validator.

Covers:
  (a) required-keys presence check (from schema/finding.schema.json)
  (b) status enum membership (from schema/finding.schema.json)
  (c) PoT-2 evidence discipline (Fact/Claim → Citation+Proof within ~12 lines),
      gated on status == "draft-complete" only.
"""
import pytest
from scripts.draft.validate import validate_finding, FindingInvalid
from scripts.draft.model import FindingDoc
from scripts.draft.templates.dependency_cve__npm import build
from scripts.verify.model import Verdict, EvidenceCapture, VERDICT_VERIFIED
from scripts.recon.advisories import Advisory


def _verdict(target="left-pad@1.0.0"):
    return Verdict(
        hypothesis_id="h",
        program_slug="huntr-npm-left-pad",
        target_identifier=target,
        vuln_class="dependency-cve",
        verdict=VERDICT_VERIFIED,
        reason="redos triggers",
        strategy="templated",
        template_id="npm:left-pad:CVE-PROPOSED",
        evidence=[
            EvidenceCapture(
                phase="trigger",
                exit_code=0,
                stdout_sha256="a" * 64,
                timed_out=False,
                duration_s=0.4,
            )
        ],
        verified_at="2026-06-22T00:00:00Z",
    )


def _same_pkg_advisory():
    return Advisory(
        id="GHSA-z",
        cve="CVE-2024-0001",
        source="osv",
        severity="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        affected_range="<1.0.1",
        fixed="1.0.1",
        package="left-pad",
    )


def _real_trace_id(doc):
    """Simulate the Task 10 drafter overwriting trace_id before validation."""
    fm = dict(doc.frontmatter)
    fm["trace_id"] = "FIND-2026-06-22-001"
    return FindingDoc(frontmatter=fm, body=doc.body, status=doc.status)


def test_draft_complete_from_template_passes():
    doc = _real_trace_id(build(_verdict(), [_same_pkg_advisory()]))  # advisory => draft-complete
    assert doc.status == "draft-complete"
    validate_finding(doc)  # must not raise


def test_draft_incomplete_from_template_passes():
    doc = _real_trace_id(build(_verdict(), []))  # no advisory => draft-incomplete; PoT-2 relaxed
    assert doc.status == "draft-incomplete"
    validate_finding(doc)  # must not raise


def test_missing_required_field_raises():
    doc = _real_trace_id(build(_verdict(), [_same_pkg_advisory()]))
    fm = dict(doc.frontmatter)
    del fm["vuln_class"]
    with pytest.raises(FindingInvalid):
        validate_finding(FindingDoc(frontmatter=fm, body=doc.body, status=doc.status))


def test_unknown_status_raises():
    doc = _real_trace_id(build(_verdict(), [_same_pkg_advisory()]))
    fm = dict(doc.frontmatter)
    fm["status"] = "bogus-status"
    with pytest.raises(FindingInvalid):
        validate_finding(FindingDoc(frontmatter=fm, body=doc.body, status="bogus-status"))


def test_fact_without_citation_raises_when_complete():
    doc = _real_trace_id(build(_verdict(), [_same_pkg_advisory()]))
    bad_body = "**Fact**: an unbacked claim.\n\n\nfiller line\nfiller line\n"
    with pytest.raises(FindingInvalid):
        validate_finding(FindingDoc(frontmatter=doc.frontmatter, body=bad_body, status="draft-complete"))


def test_fact_without_citation_ok_when_incomplete():
    doc = _real_trace_id(build(_verdict(), []))
    validate_finding(
        FindingDoc(
            frontmatter=doc.frontmatter,
            body="**Fact**: tbd, no citation yet.\n",
            status="draft-incomplete",
        )
    )
