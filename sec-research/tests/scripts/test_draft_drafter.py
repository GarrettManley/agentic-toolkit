# tests/scripts/test_draft_drafter.py
from pathlib import Path
import pytest
from scripts.draft.drafter import draft_findings
from scripts.verify.model import Verdict, EvidenceCapture, VERDICT_VERIFIED

def _novel(target="left-pad@1.0.0", vuln_class="dependency-cve", template_id="npm:left-pad:CVE-PROPOSED"):
    return Verdict(hypothesis_id="h", program_slug="huntr-npm-left-pad", target_identifier=target,
                   vuln_class=vuln_class, verdict=VERDICT_VERIFIED, reason="redos", strategy="templated",
                   template_id=template_id,
                   evidence=[EvidenceCapture(phase="trigger", exit_code=0, stdout_sha256="a"*64,
                                             timed_out=False, duration_s=0.3)],
                   verified_at="2026-06-22T00:00:00Z")

@pytest.fixture(autouse=True)
def _isolate_ledger(monkeypatch):
    # patch the ledger the drafter uses so the test never touches submissions/ledger.jsonl
    import scripts.draft.drafter as d
    class _Cap:
        def __init__(self): self.events = []
        def append_event(self, et, **f): self.events.append((et, f)); return {}
    monkeypatch.setattr(d, "ledger", _Cap(), raising=False)

def test_drafts_finding_to_disk(tmp_path: Path):
    results = draft_findings([_novel()], [], findings_root=tmp_path, today="2026-06-22")
    assert len(results) == 1
    r = results[0]
    assert r.trace_id == "FIND-2026-06-22-001"
    finding = tmp_path / r.trace_id / "finding.md"
    assert finding.exists()
    text = finding.read_text(encoding="utf-8")
    assert "trace_id" in text and "left-pad@1.0.0" in text
    assert "FIND-PENDING" not in text  # placeholder was overwritten
    assert (tmp_path / r.trace_id / "evidence" / "redacted" / "sandbox_stdout.txt").exists()

def test_unregistered_class_is_skipped(tmp_path):
    v = _novel(vuln_class="unknown-class", template_id="cargo:x:CVE-PROPOSED")
    assert draft_findings([v], [], findings_root=tmp_path, today="2026-06-22") == []

def test_second_finding_gets_incremented_trace_id(tmp_path):
    r1 = draft_findings([_novel()], [], findings_root=tmp_path, today="2026-06-22")
    r2 = draft_findings([_novel()], [], findings_root=tmp_path, today="2026-06-22")
    assert r1[0].trace_id == "FIND-2026-06-22-001"
    assert r2[0].trace_id == "FIND-2026-06-22-002"
