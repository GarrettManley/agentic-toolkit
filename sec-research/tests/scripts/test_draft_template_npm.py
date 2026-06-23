"""Tests for scripts/draft/templates/dependency_cve__npm.py — Stage 6 npm finding template."""
import pytest
from scripts.draft.templates.dependency_cve__npm import build
from scripts.draft.errors import IncompleteVerdict
from scripts.verify.model import Verdict, EvidenceCapture, VERDICT_VERIFIED
from scripts.recon.advisories import Advisory


def _v(target="left-pad@1.0.0", evidence=None):
    return Verdict(
        hypothesis_id="h",
        program_slug="huntr-npm-left-pad",
        target_identifier=target,
        vuln_class="dependency-cve",
        verdict=VERDICT_VERIFIED,
        reason="redos triggers",
        strategy="templated",
        template_id="npm:left-pad:CVE-PROPOSED",
        evidence=evidence or [
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


def _advisory(package="left-pad", cve="CVE-2022-0001"):
    return Advisory(
        id="GHSA-test-0001-abcd",
        cve=cve,
        source="osv",
        severity="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        affected_range="<1.3.0",
        fixed="1.3.0",
        package=package,
    )


def test_build_fills_structural_frontmatter_and_poc():
    doc = build(_v(), [])
    fm = doc.frontmatter
    assert fm["vuln_class"] == "dependency-cve"
    assert fm["target"]["identifier"] == "left-pad@1.0.0"
    assert fm["target"]["ecosystem"] == "npm"
    assert fm["poc"]["expected_exit_code"] == 0
    assert fm["poc"]["expected_output_hash"] == "a" * 64
    assert fm["poc"]["deterministic"] is True


def test_body_has_fact_citation_proof():
    doc = build(_v(), [])
    low = doc.body.lower()
    assert "fact" in low and "citation" in low and "proof" in low


def test_novel_finding_is_draft_incomplete_without_advisory():
    doc = build(_v(), [])
    assert doc.status == "draft-incomplete"  # no semantic advisory → honest gradient


def test_unparseable_target_raises():
    with pytest.raises(IncompleteVerdict):
        build(_v(target="not-a-package-spec"), [])


def test_scoped_package_parses_correctly():
    """Scoped packages like @scope/pkg@1.2.3 split correctly via rpartition."""
    doc = build(_v(target="@scope/pkg@1.2.3"), [])
    fm = doc.frontmatter
    assert fm["target"]["identifier"] == "@scope/pkg@1.2.3"
    assert fm["title"].startswith("@scope/pkg@1.2.3")


def test_build_with_same_package_advisory_is_draft_complete():
    """A same-package advisory supplies semantic fields → draft-complete."""
    adv = _advisory(package="left-pad")
    doc = build(_v(), [adv])
    assert doc.status == "draft-complete"
    fm = doc.frontmatter
    assert fm["cwe_ids"] is not None
    assert fm["severity"]["cvss_v3_1_vector"].startswith("CVSS:3.1/")
    assert fm["severity"]["cvss_v3_1_score"] >= 0.0


def test_build_with_different_package_advisory_is_draft_incomplete():
    """Advisory for a different package does NOT satisfy semantic fields."""
    adv = _advisory(package="other-package")
    doc = build(_v(), [adv])
    assert doc.status == "draft-incomplete"


def test_poc_falls_back_to_last_evidence_when_no_trigger_phase():
    """When no phase=='trigger' evidence exists, fall back to last entry."""
    install_only = [
        EvidenceCapture(phase="install", exit_code=0, stdout_sha256="b" * 64,
                        timed_out=False, duration_s=0.1)
    ]
    doc = build(_v(evidence=install_only), [])
    assert doc.frontmatter["poc"]["expected_output_hash"] == "b" * 64


def test_deduplication_check_structure():
    """deduplication_check uses schema enum values for checked_against."""
    doc = build(_v(), [])
    dc = doc.frontmatter["deduplication_check"]
    assert "matches" in dc
    assert dc["matches"] == []
    assert isinstance(dc["checked_against"], list)
    assert len(dc["checked_against"]) >= 1
    # All values must be from the schema enum
    valid = {"nvd", "ghsa", "osv", "program-disclosed", "venue-dupe-api"}
    for v in dc["checked_against"]:
        assert v in valid


def test_required_schema_fields_present():
    """Top-level required keys per schema are all present."""
    doc = build(_v(), [])
    fm = doc.frontmatter
    required = {"trace_id", "title", "program_slug", "vuln_class", "severity",
                "status", "discovered_at", "target", "evidence", "poc",
                "citations", "deduplication_check"}
    assert required.issubset(fm.keys())


def test_evidence_has_required_schema_shape():
    """evidence must have exactly timeline_path/redacted_dir/verification_path."""
    doc = build(_v(), [])
    ev = doc.frontmatter["evidence"]
    assert ev["timeline_path"] == "timeline.md"
    assert ev["redacted_dir"] == "evidence/redacted/"
    assert ev["verification_path"] == "verification.json"


def test_citations_nonempty():
    """citations must have at least one entry."""
    doc = build(_v(), [])
    assert len(doc.frontmatter["citations"]) >= 1
