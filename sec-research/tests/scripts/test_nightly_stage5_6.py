"""Tests for nightly Stage 5 (stage_triage) and Stage 6 (stage_draft_findings).

Task 5 — wire stage_triage into the nightly pipeline.

stage_triage(verdicts, slug, *, now) -> list[Verdict]
  - drops verified verdicts whose template_id CVE matches a loaded advisory
  - returns novel verified verdicts (no advisory match)
  - calls persist_triage (monkeypatched so no disk I/O in unit tests)

Task 11 — wire stage_draft_findings into the nightly pipeline.

stage_draft_findings(novel, slug, *, today) -> list[str]
  - calls draft_findings with slug's advisories (via load_advisories) and FINDINGS_ROOT
  - returns list of trace_ids for drafted findings
  - FINDINGS_ROOT is module-level and patchable; tests redirect to tmp_path

Monkeypatch convention: target the module object directly (same pattern as
test_nightly_stage_verify.py → monkeypatch.setattr(nightly, "verify_hypotheses", ...)).
The names load_advisories and persist_triage are imported at module level in
nightly.py so monkeypatching them on the nightly module object controls what
stage_triage calls at runtime.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _v(template_id):
    from verify.model import Verdict, VERDICT_VERIFIED
    return Verdict(
        hypothesis_id="h",
        program_slug="huntr-npm-minimatch",
        target_identifier="minimatch@3.0.4",
        vuln_class="dependency-cve",
        verdict=VERDICT_VERIFIED,
        reason="ok",
        strategy="templated",
        template_id=template_id,
        evidence=[],
        verified_at="t",
    )


def test_stage_triage_drops_known_cve(monkeypatch, tmp_path):
    """A verdict whose CVE matches a loaded advisory is dropped; novel one is kept."""
    from recon.advisories import Advisory
    import nightly

    monkeypatch.setattr(
        nightly,
        "load_advisories",
        lambda slug, **kw: [Advisory(
            id="GHSA-x",
            cve="CVE-2022-3517",
            source="osv",
            severity="7.5",
            affected_range="<3.0.5",
            fixed="3.0.5",
            package="minimatch",
        )],
    )
    monkeypatch.setattr(nightly, "persist_triage", lambda *a, **k: tmp_path / "t.json")

    novel = nightly.stage_triage(
        [_v("npm:minimatch:CVE-2022-3517"), _v("npm:left-pad:CVE-2099-0001")],
        "huntr-npm-minimatch",
        now="t",
    )
    assert [v.template_id for v in novel] == ["npm:left-pad:CVE-2099-0001"]


def test_stage_triage_all_novel(monkeypatch, tmp_path):
    """All verdicts are novel when there are no matching advisories."""
    import nightly

    monkeypatch.setattr(nightly, "load_advisories", lambda slug, **kw: [])
    monkeypatch.setattr(nightly, "persist_triage", lambda *a, **k: tmp_path / "t.json")

    novel = nightly.stage_triage(
        [_v("npm:left-pad:CVE-2099-0001"), _v("npm:lodash:CVE-2099-0002")],
        "huntr-npm-minimatch",
        now="t",
    )
    assert len(novel) == 2


def test_stage_triage_persist_called(monkeypatch, tmp_path):
    """persist_triage must be called exactly once per stage_triage invocation."""
    import nightly

    monkeypatch.setattr(nightly, "load_advisories", lambda slug, **kw: [])
    calls = []
    monkeypatch.setattr(
        nightly,
        "persist_triage",
        lambda slug, results, **kw: calls.append((slug, results)) or tmp_path / "t.json",
    )

    nightly.stage_triage([_v("npm:x:CVE-2099-9")], "my-slug", now="2026-01-01T00:00:00Z")
    assert len(calls) == 1
    assert calls[0][0] == "my-slug"


def test_stage_draft_findings_writes_for_novel(monkeypatch, tmp_path):
    """stage_draft_findings drafts a finding file for a novel VERDICT_VERIFIED verdict."""
    import nightly
    import scripts.draft.drafter as _drafter
    from verify.model import Verdict, EvidenceCapture, VERDICT_VERIFIED

    # Redirect FINDINGS_ROOT to tmp_path so no real findings/ dir is touched.
    monkeypatch.setattr(nightly, "FINDINGS_ROOT", tmp_path, raising=False)
    # load_advisories returns empty list (no known advisories for this slug).
    monkeypatch.setattr(nightly, "load_advisories", lambda slug, **kw: [])
    # Patch the ledger inside the drafter so no submissions/ledger.jsonl is written.
    class _FakeLedger:
        def append_event(self, event_type, **fields):
            return {}
    monkeypatch.setattr(_drafter, "ledger", _FakeLedger(), raising=False)

    v = Verdict(
        hypothesis_id="h",
        program_slug="huntr-npm-left-pad",
        target_identifier="left-pad@1.0.0",
        vuln_class="dependency-cve",
        verdict=VERDICT_VERIFIED,
        reason="redos",
        strategy="templated",
        template_id="npm:left-pad:CVE-PROPOSED",
        evidence=[EvidenceCapture(
            phase="trigger", exit_code=0, stdout_sha256="a" * 64,
            timed_out=False, duration_s=0.3,
        )],
        verified_at="t",
    )
    ids = nightly.stage_draft_findings([v], "huntr-npm-left-pad", today="2026-06-22")
    assert ids == ["FIND-2026-06-22-001"]
    assert (tmp_path / "FIND-2026-06-22-001" / "finding.md").exists()


def test_verdict_from_dict_rebuilds_evidence():
    """_verdict_from_dict must reconstruct nested EvidenceCapture objects.

    verify_hypotheses returns dicts (via asdict()), so evidence entries are dicts.
    Stage 6 will access verdict.evidence[i].exit_code via attribute — this test
    guards that the reconstruction path produces EvidenceCapture instances, not dicts.
    """
    import nightly
    from verify.model import EvidenceCapture, Verdict, VERDICT_VERIFIED

    vd = {
        "hypothesis_id": "h-001",
        "program_slug": "huntr-npm-minimatch",
        "target_identifier": "minimatch@3.0.4",
        "vuln_class": "dependency-cve",
        "verdict": VERDICT_VERIFIED,
        "reason": "exit+sha match",
        "strategy": "templated",
        "template_id": "npm:minimatch:CVE-2022-3517",
        "evidence": [
            {
                "phase": "install",
                "exit_code": 0,
                "stdout_sha256": "abc123",
                "timed_out": False,
                "duration_s": 1.2,
            },
            {
                "phase": "trigger",
                "exit_code": 1,
                "stdout_sha256": "def456",
                "timed_out": False,
                "duration_s": 0.4,
            },
        ],
        "verified_at": "2026-06-22T00:00:00Z",
        "verified": True,  # harness-added key; must be stripped
    }

    result = nightly._verdict_from_dict(vd)

    assert isinstance(result, Verdict)
    assert len(result.evidence) == 2
    assert isinstance(result.evidence[0], EvidenceCapture)
    assert result.evidence[0].exit_code == 0
    assert result.evidence[0].stdout_sha256 == "abc123"
    assert isinstance(result.evidence[1], EvidenceCapture)
    assert result.evidence[1].exit_code == 1
    assert result.evidence[1].stdout_sha256 == "def456"
