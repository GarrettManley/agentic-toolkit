"""Tests for nightly.stage_triage — Stage 5 wire-up.

Task 5 — wire stage_triage into the nightly pipeline.

stage_triage(verdicts, slug, *, now) -> list[Verdict]
  - drops verified verdicts whose template_id CVE matches a loaded advisory
  - returns novel verified verdicts (no advisory match)
  - calls persist_triage (monkeypatched so no disk I/O in unit tests)

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
    from scripts.verify.model import Verdict, VERDICT_VERIFIED
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
    from scripts.recon.advisories import Advisory
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
