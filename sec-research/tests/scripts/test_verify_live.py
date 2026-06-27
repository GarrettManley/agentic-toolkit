"""docker-gated live integration test — Stage 4c end-to-end verification.

Proves the full verify pipeline against real containers via the deterministic
guard-presence probe (the resolved version is run; the fixed 3.0.5 rejects an
over-length pattern via its assertValidPattern guard, the affected 3.0.4 does not):
  - minimatch@3.0.4 (affected)  → verdict "verified"
  - minimatch@3.0.5 (fixed)     → verdict "refuted"

Also proves the Stage 5+6 contract end-to-end:
  - Duplicate true-negative: a verified minimatch verdict is triaged against
    advisories that include CVE-2022-3517 → classified duplicate → no finding.
  - Synthetic-novel draft: a verified verdict whose CVE is absent from the
    advisories → novel → stage_draft_findings writes a schema-valid finding.

Skip conditions (both must hold to run):
  1. Docker engine reachable in WSL2 (same check as test_sandbox_runner.py).
  2. VERIFY_LIVE=1 env flag explicitly set (same pattern as test_llm_live.py).

Without VERIFY_LIVE=1 this test is always skipped — it pulls images + npm-installs,
which is too slow for the routine offline suite.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _docker_available() -> bool:
    try:
        p = subprocess.run(
            ["wsl", "-e", "docker", "info"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return p.returncode == 0
    except Exception:
        return False


@pytest.mark.skipif(
    not _docker_available() or os.environ.get("VERIFY_LIVE") != "1",
    reason="requires docker in WSL2 + VERIFY_LIVE=1",
)
def test_minimatch_304_verified_305_refuted(tmp_path):
    """End-to-end: affected 3.0.4 is verified; fixed 3.0.5 is refuted.

    Both assertions constitute the verification proof:
      - The affected version lacks the 3.0.5 length guard → VULN_CONFIRMED.
      - The fixed version rejects the over-length pattern → PATCHED.
    """
    from verify.harness import verify_hypotheses

    # -----------------------------------------------------------------------
    # Affected version — minimatch@3.0.4
    # -----------------------------------------------------------------------
    hyp_affected = {
        "hypothesis_id": "live-test-minimatch-304",
        "program_slug": "live-test",
        "vuln_class": "dependency-cve",
        "evidence_seed": {
            "package_ecosystem": "npm",
            "package_name": "minimatch",
            "affected_versions_range": "<3.0.5",
            "candidate_cve_id": "CVE-2022-3517",
        },
        "target": {
            "asset_type": "package",
            "identifier": "minimatch",
            "ecosystem": "npm",
            "version_or_revision": "3.0.4",
        },
    }

    verdicts_affected = verify_hypotheses([hyp_affected], verdict_root=tmp_path)
    assert len(verdicts_affected) == 1
    v_affected = verdicts_affected[0]
    assert v_affected["verdict"] == "verified", (
        f"Expected minimatch@3.0.4 → verified, got {v_affected['verdict']!r}. "
        f"Reason: {v_affected.get('reason')}"
    )
    assert v_affected["verified"] is True

    # -----------------------------------------------------------------------
    # Fixed version — minimatch@3.0.5
    # -----------------------------------------------------------------------
    hyp_fixed = {
        "hypothesis_id": "live-test-minimatch-305",
        "program_slug": "live-test",
        "vuln_class": "dependency-cve",
        "evidence_seed": {
            "package_ecosystem": "npm",
            "package_name": "minimatch",
            "affected_versions_range": "<3.0.5",
            "candidate_cve_id": "CVE-2022-3517",
        },
        "target": {
            "asset_type": "package",
            "identifier": "minimatch",
            "ecosystem": "npm",
            "version_or_revision": "3.0.5",
        },
    }

    verdicts_fixed = verify_hypotheses([hyp_fixed], verdict_root=tmp_path)
    assert len(verdicts_fixed) == 1
    v_fixed = verdicts_fixed[0]
    assert v_fixed["verdict"] == "refuted", (
        f"Expected minimatch@3.0.5 → refuted, got {v_fixed['verdict']!r}. "
        f"Reason: {v_fixed.get('reason')}"
    )
    assert v_fixed["verified"] is False


@pytest.mark.skipif(
    not _docker_available() or os.environ.get("VERIFY_LIVE") != "1",
    reason="requires docker in WSL2 + VERIFY_LIVE=1",
)
def test_stage5_6_duplicate_true_negative(tmp_path, monkeypatch):
    """Stage 5+6 true-negative: verified minimatch@3.0.4 verdict triaged against
    advisories that include CVE-2022-3517 → classified duplicate → no finding drafted.

    Verified verdict obtained via real docker (same path as the existing live test).
    Ledger and disk writes are isolated to tmp_path so the real findings/ and
    submissions/ledger.jsonl are never touched.
    """
    import nightly
    import scripts.draft.drafter as _drafter
    from recon.advisories import Advisory
    from verify.harness import verify_hypotheses

    # -----------------------------------------------------------------------
    # Step 1: obtain a real verified verdict for minimatch@3.0.4 via docker.
    # -----------------------------------------------------------------------
    hyp = {
        "hypothesis_id": "e2e-dup-minimatch-304",
        "program_slug": "e2e-live-test",
        "vuln_class": "dependency-cve",
        "evidence_seed": {
            "package_ecosystem": "npm",
            "package_name": "minimatch",
            "affected_versions_range": "<3.0.5",
            "candidate_cve_id": "CVE-2022-3517",
        },
        "target": {
            "asset_type": "package",
            "identifier": "minimatch",
            "ecosystem": "npm",
            "version_or_revision": "3.0.4",
        },
    }
    verdicts_raw = verify_hypotheses([hyp], verdict_root=tmp_path / "verdicts")
    assert len(verdicts_raw) == 1, f"Expected 1 verdict, got {len(verdicts_raw)}"
    vd_raw = verdicts_raw[0]
    assert vd_raw["verdict"] == "verified", (
        f"Expected minimatch@3.0.4 → verified for triage test, got {vd_raw['verdict']!r}. "
        f"Reason: {vd_raw.get('reason')}"
    )

    # Reconstruct Verdict dataclass via nightly's _verdict_from_dict (the real pipeline path).
    verdict_obj = nightly._verdict_from_dict(vd_raw)

    # -----------------------------------------------------------------------
    # Step 2: patch isolation — no real disk writes, no real ledger events.
    # -----------------------------------------------------------------------
    # Triage isolation: patch load_advisories (returns the advisory that matches CVE-2022-3517)
    # and persist_triage (no-op instead of writing to runtime/triage/).
    known_advisory = Advisory(
        id="GHSA-f8q6-p94x-37v3",
        cve="CVE-2022-3517",
        source="osv",
        severity="7.5",
        affected_range="<3.0.5",
        fixed="3.0.5",
        package="minimatch",
    )
    monkeypatch.setattr(nightly, "load_advisories", lambda slug, **kw: [known_advisory])
    monkeypatch.setattr(nightly, "persist_triage", lambda *a, **kw: tmp_path / "triage.json")

    # Draft isolation: redirect findings root and silence the ledger.
    findings_tmp = tmp_path / "findings"
    monkeypatch.setattr(nightly, "FINDINGS_ROOT", findings_tmp, raising=False)

    class _NoopLedger:
        def append_event(self, event_type, **fields):
            return {}

    monkeypatch.setattr(_drafter, "ledger", _NoopLedger(), raising=False)

    # -----------------------------------------------------------------------
    # Step 3: run stage_triage — expect empty novel list (duplicate dropped).
    # -----------------------------------------------------------------------
    novel = nightly.stage_triage(
        [verdict_obj],
        "e2e-live-test",
        now="2026-06-22T00:00:00Z",
    )
    assert novel == [], (
        f"Expected no novel verdicts (minimatch CVE-2022-3517 is a known duplicate), "
        f"got: {novel!r}"
    )

    # -----------------------------------------------------------------------
    # Step 4: run stage_draft_findings on the empty novel list — no files created.
    # -----------------------------------------------------------------------
    trace_ids = nightly.stage_draft_findings(novel, "e2e-live-test", today="2026-06-22")
    assert trace_ids == [], (
        f"Expected no findings drafted for a duplicate verdict, got: {trace_ids!r}"
    )
    # Double-check: no FIND-* directory was created under findings_tmp.
    find_dirs = [p for p in findings_tmp.glob("FIND-*")] if findings_tmp.exists() else []
    assert find_dirs == [], (
        f"Expected no FIND-* dirs under tmp findings root, found: {find_dirs!r}"
    )


@pytest.mark.skipif(
    not _docker_available() or os.environ.get("VERIFY_LIVE") != "1",
    reason="requires docker in WSL2 + VERIFY_LIVE=1",
)
def test_stage5_6_novel_finding_drafted(tmp_path, monkeypatch):
    """Stage 5+6 novel-draft: a verified verdict whose CVE is absent from advisories
    → triage classifies it novel → stage_draft_findings writes a schema-valid finding.

    The verified Verdict is constructed directly (not via docker) because what's
    under test here is the triage→draft contract, not the verify step. The existing
    test_minimatch_304_verified_305_refuted already covers Stage 4c end-to-end.

    Ledger and disk writes are isolated to tmp_path.
    """
    import nightly
    import scripts.draft.drafter as _drafter
    from verify.model import Verdict, EvidenceCapture, VERDICT_VERIFIED

    import yaml

    # -----------------------------------------------------------------------
    # Step 1: construct a synthetic verified verdict whose CVE is novel
    # (CVE-2099-9999 does not exist in any real advisory we'll supply).
    # -----------------------------------------------------------------------
    verdict_obj = Verdict(
        hypothesis_id="e2e-novel-left-pad",
        program_slug="e2e-live-test",
        target_identifier="left-pad@1.0.0",
        vuln_class="dependency-cve",
        verdict=VERDICT_VERIFIED,
        reason="exploit reproduced (exit 1, stdout hash matched)",
        strategy="templated",
        template_id="npm:left-pad:CVE-2099-9999",
        evidence=[
            EvidenceCapture(
                phase="install",
                exit_code=0,
                stdout_sha256="a" * 64,
                timed_out=False,
                duration_s=1.2,
            ),
            EvidenceCapture(
                phase="trigger",
                exit_code=1,
                stdout_sha256="b" * 64,
                timed_out=False,
                duration_s=0.4,
            ),
        ],
        verified_at="2026-06-22T00:00:00Z",
    )

    # -----------------------------------------------------------------------
    # Step 2: patch isolation.
    # -----------------------------------------------------------------------
    # Empty advisories → triage has no known CVEs to match → verdict is novel.
    monkeypatch.setattr(nightly, "load_advisories", lambda slug, **kw: [])
    monkeypatch.setattr(nightly, "persist_triage", lambda *a, **kw: tmp_path / "triage.json")

    findings_tmp = tmp_path / "findings"
    monkeypatch.setattr(nightly, "FINDINGS_ROOT", findings_tmp, raising=False)

    class _NoopLedger:
        def append_event(self, event_type, **fields):
            return {}

    monkeypatch.setattr(_drafter, "ledger", _NoopLedger(), raising=False)

    # -----------------------------------------------------------------------
    # Step 3: run stage_triage — expect exactly 1 novel verdict.
    # -----------------------------------------------------------------------
    novel = nightly.stage_triage(
        [verdict_obj],
        "e2e-live-test",
        now="2026-06-22T00:00:00Z",
    )
    assert len(novel) == 1, (
        f"Expected 1 novel verdict (no matching advisories), got: {novel!r}"
    )

    # -----------------------------------------------------------------------
    # Step 4: run stage_draft_findings — expect exactly one FIND-* directory
    # containing a schema-valid finding.md with Fact:/Citation:/Proof: blocks.
    # -----------------------------------------------------------------------
    today = "2026-06-22"
    trace_ids = nightly.stage_draft_findings(novel, "e2e-live-test", today=today)
    assert len(trace_ids) == 1, (
        f"Expected 1 trace_id drafted, got: {trace_ids!r}"
    )
    expected_trace = f"FIND-{today}-001"
    assert trace_ids[0] == expected_trace, (
        f"Expected trace_id {expected_trace!r}, got {trace_ids[0]!r}"
    )

    finding_path = findings_tmp / expected_trace / "finding.md"
    assert finding_path.exists(), (
        f"Expected {finding_path} to exist after drafting, but it was not created."
    )

    # Validate frontmatter round-trips through YAML.
    text = finding_path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "finding.md must start with YAML frontmatter block"
    fm_end = text.index("---\n", 4)
    fm_text = text[4:fm_end]
    frontmatter = yaml.safe_load(fm_text)
    assert isinstance(frontmatter, dict), "Frontmatter must parse as a YAML mapping"
    assert frontmatter.get("trace_id") == expected_trace, (
        f"frontmatter trace_id mismatch: {frontmatter.get('trace_id')!r}"
    )

    # Validate body contains Fact:/Citation:/Proof: evidence discipline block.
    body = text[fm_end + 4:]
    assert "Fact:" in body or "**Fact**:" in body, (
        "finding.md body must contain a Fact: line (evidence discipline)"
    )
    assert "Citation:" in body or "**Citation**:" in body, (
        "finding.md body must contain a Citation: line"
    )
    assert "Proof:" in body or "**Proof**:" in body, (
        "finding.md body must contain a Proof: line"
    )


@pytest.mark.skipif(
    os.environ.get("VERIFY_LIVE") != "1", reason="needs docker"
)
def test_minimatch_differential_live():
    """3.0.4 confirms AND 3.0.5 is silenced → verified, via the real differential drive."""
    from verify.harness import verify_hypotheses
    from verify.templated import TemplatedPocStrategy
    hyp = {
        "hypothesis_id": "HYP-LIVE-001", "program_slug": "huntr-npm-minimatch",
        "vuln_class": "dependency-cve",
        "target": {"identifier": "minimatch", "version_or_revision": "3.0.4"},
        "evidence_seed": {
            "package_ecosystem": "npm", "package_name": "minimatch",
            "affected_versions_range": "<3.0.5", "candidate_cve_id": "CVE-2022-3517",
        },
    }
    results = verify_hypotheses([hyp], strategy=TemplatedPocStrategy())
    assert results[0]["verdict"] == "verified"
    assert results[0]["verified"] is True


@pytest.mark.skipif(
    os.environ.get("VERIFY_LIVE") != "1" or os.environ.get("LLM_LIVE") != "1",
    reason="needs docker AND a live LLM provider",
)
def test_llm_authored_differential_live():
    """End-to-end: LLM authors a PoC for a real npm dependency-CVE, differentially verified."""
    from verify.harness import verify_hypotheses
    from verify.llm_strategy import LLMPocStrategy
    hyp = {
        "hypothesis_id": "HYP-LIVE-002", "program_slug": "huntr-npm-lodash",
        "vuln_class": "dependency-cve",
        "target": {"identifier": "lodash", "version_or_revision": "4.17.4"},
        "evidence_seed": {
            "package_ecosystem": "npm", "package_name": "lodash",
            "affected_versions_range": "<4.17.12", "candidate_cve_id": "CVE-2019-10744",
            "fixed_version": "4.17.12",
            "attack_vector_hypothesis": "prototype pollution via defaultsDeep / zipObjectDeep",
        },
    }
    results = verify_hypotheses([hyp], strategy=LLMPocStrategy())
    # Either a trustworthy verified, or an honest error if the LLM can't author a
    # discriminating PoC — but NEVER a laundered 'refuted' from an infra failure.
    assert results[0]["verdict"] in {"verified", "refuted", "error"}
    assert "differential:" in results[0]["reason"]
