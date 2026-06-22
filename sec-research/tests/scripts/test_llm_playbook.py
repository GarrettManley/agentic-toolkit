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
