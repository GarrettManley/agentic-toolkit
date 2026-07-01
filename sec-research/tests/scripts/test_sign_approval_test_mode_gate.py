"""End-to-end proof that sign_approval.py's --test-mode-confirm refuses to bypass the
interactive confirmation outside a pytest process (design §3)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _WORKSPACE_ROOT / "scripts"
for _p in (_WORKSPACE_ROOT, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@pytest.fixture(autouse=True)
def _isolate_ledger(monkeypatch):
    """draft_findings() and sign_approval.main() each append real ledger events
    ("draft-created", "approval-issued"); capture them instead of writing to the real,
    git-ignored-but-locally-persisted submissions/ledger.jsonl.

    Patched on the canonical lib.ledger module -- not on drafter's or sign_approval's
    locally-bound `ledger` name -- because this test's sys.path makes
    scripts/draft/drafter.py importable under two distinct module identities
    (`scripts.draft.drafter` and `draft.drafter`; Python treats these as separate
    module objects, each with its own `ledger` attribute binding, so patching only one
    leaves callers of the other unpatched). lib.ledger itself has exactly one
    resolvable location on this sys.path, so every caller's
    `from lib import ledger; ledger.append_event(...)` resolves `append_event` via
    attribute lookup on that single shared object at call time -- patching it here
    isolates every caller uniformly, regardless of which drafter/sign_approval import
    spelling it used."""
    import lib.ledger as ledger_module
    events: list[tuple[str, dict]] = []
    def _fake_append_event(event_type, **fields):
        events.append((event_type, fields))
        return {}
    monkeypatch.setattr(ledger_module, "append_event", _fake_append_event)


def _draft_verified_finding(tmp_path: Path) -> str:
    """Draft one real, schema-valid finding via the existing drafter (same pattern as
    tests/scripts/test_draft_drafter.py) and drop a passing verification.json next to
    it, so sign_approval.py's pre-checks succeed before reaching the confirm step."""
    from draft.drafter import draft_findings
    from verify.model import Verdict, EvidenceCapture, VERDICT_VERIFIED

    verdict = Verdict(
        hypothesis_id="h", program_slug="huntr-npm-test-target",
        target_identifier="left-pad@1.0.0", vuln_class="dependency-cve",
        verdict=VERDICT_VERIFIED, reason="redos", strategy="templated",
        template_id="npm:left-pad:CVE-PROPOSED",
        evidence=[EvidenceCapture(phase="trigger", exit_code=0, stdout_sha256="a" * 64,
                                  timed_out=False, duration_s=0.3)],
        verified_at="2026-07-01T00:00:00Z",
    )
    results = draft_findings([verdict], [], findings_root=tmp_path, today="2026-07-01")
    trace_id = results[0].trace_id
    finding_dir = tmp_path / trace_id
    (finding_dir / "verification.json").write_text(
        json.dumps({"ok": True, "verified_at": "2026-07-01T00:00:00Z"}), encoding="utf-8",
    )
    return trace_id


def test_test_mode_confirm_refused_outside_pytest(override_key_setup, clean_overrides, tmp_path, monkeypatch):
    import sign_approval
    trace_id = _draft_verified_finding(tmp_path)
    monkeypatch.setattr(sign_approval, "FINDINGS_DIR", tmp_path)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "sign_approval.py", trace_id, "--venue", "huntr", "--test-mode-confirm",
    ])

    rc = sign_approval.main()
    assert rc == 1

    tokens_dir = sign_approval.SUBMISSIONS_TOKENS_DIR
    assert not tokens_dir.exists() or not list(tokens_dir.glob("apv-*.json"))


def test_test_mode_confirm_still_works_under_pytest(override_key_setup, clean_overrides, tmp_path, monkeypatch):
    """Symmetric happy-path check (parity with sign_override.py's paired test): the
    gate must not break the legitimate case, where PYTEST_CURRENT_TEST is genuinely set
    by pytest itself for the duration of this very test."""
    import sign_approval
    trace_id = _draft_verified_finding(tmp_path)
    monkeypatch.setattr(sign_approval, "FINDINGS_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "sign_approval.py", trace_id, "--venue", "huntr", "--test-mode-confirm",
    ])

    rc = sign_approval.main()
    assert rc == 0

    tokens_dir = sign_approval.SUBMISSIONS_TOKENS_DIR
    assert list(tokens_dir.glob("apv-*.json"))
