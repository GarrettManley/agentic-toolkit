from __future__ import annotations
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]


def test_seed_playbook_parses():
    from llm.playbook import parse_playbook
    pb = parse_playbook(REPO / "playbooks" / "dependency-cve" / "known-advisory-confirmation.md")
    assert pb.vuln_class == "dependency-cve"
    assert pb.technique == "known-advisory-confirmation"
    assert pb.trace_id == "trace-pb-2026-06-22-001"
    assert any("known_advisories" in s for s in pb.positive_signals)
    assert pb.negative_signals  # non-empty
    assert pb.citations


def test_load_playbooks_skips_meta(tmp_path):
    from llm.playbook import load_playbooks
    (tmp_path / "_meta").mkdir()
    (tmp_path / "_meta" / "accepted-patterns.md").write_text("# x\n", encoding="utf-8")
    (tmp_path / "dependency-cve").mkdir()
    (tmp_path / "dependency-cve" / "t.md").write_text(
        "# Dependency CVE — T\n\n## Signal patterns (positive indicators)\n- a\n", encoding="utf-8")
    pbs = load_playbooks(tmp_path)
    assert [p.technique for p in pbs] == ["t"]


def test_load_empty_dir_returns_empty(tmp_path):
    from llm.playbook import load_playbooks
    assert load_playbooks(tmp_path) == []


def test_select_playbooks_requires_advisory_for_dependency_cve():
    from llm.playbook import parse_playbook, select_playbooks
    pb = parse_playbook(REPO / "playbooks" / "dependency-cve" / "known-advisory-confirmation.md")
    with_adv = {"asset": {"asset_type": "package", "ecosystem": "npm"},
                "known_advisories": [{"id": "GHSA-x"}]}
    without_adv = {"asset": {"asset_type": "package", "ecosystem": "npm"},
                   "known_advisories": []}
    assert select_playbooks(with_adv, [pb]) == [pb]
    assert select_playbooks(without_adv, [pb]) == []


def test_select_playbooks_eligible_after_ghsa_repo_asset_relabel():
    """hb-7hf regression: before the fix, a GHSA-sourced recon item's asset stayed
    asset_type='repo' with ecosystem=None forever, so this exact shape (which is what
    scripts/recon_program.py now produces post-relabel) was structurally ineligible."""
    from llm.playbook import parse_playbook, select_playbooks
    pb = parse_playbook(REPO / "playbooks" / "dependency-cve" / "known-advisory-confirmation.md")
    relabeled_ghsa_item = {
        "asset": {"asset_type": "package", "identifier": "minimatch", "ecosystem": "npm"},
        "known_advisories": [{"id": "GHSA-x"}],
    }
    assert select_playbooks(relabeled_ghsa_item, [pb]) == [pb]


def test_select_playbooks_ineligible_for_unrelabeled_ghsa_repo_asset():
    """The pre-fix shape (still asset_type='repo', ecosystem=None) correctly stays
    ineligible — proves this is a targeted fix, not a gate removal."""
    from llm.playbook import parse_playbook, select_playbooks
    pb = parse_playbook(REPO / "playbooks" / "dependency-cve" / "known-advisory-confirmation.md")
    unrelabeled_ghsa_item = {
        "asset": {"asset_type": "repo", "identifier": "github.com/isaacs/minimatch", "ecosystem": None},
        "known_advisories": [{"id": "GHSA-x"}],
    }
    assert select_playbooks(unrelabeled_ghsa_item, [pb]) == []
