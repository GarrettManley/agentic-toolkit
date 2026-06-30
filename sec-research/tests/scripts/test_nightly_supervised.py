"""Tests for the supervised driver (hb-322) and the run journal.

Covers:
- CLI: --until/--yes/--provider require --supervised
- supervised flow: --until early-stop short-circuits later stages
- supervised flow: zero-novel run finishes as a documented NULL result
- supervised flow: no scopes loaded -> exit 2 (no silent run)
- pre-flight: fails loud on a misconfigured provider AND on a down sandbox
- RunJournal: incremental header/checkpoint/finish content

Monkeypatch convention matches the other nightly tests: patch names on the `nightly`
module object (stage_* are module-level), and on `lib.journal`/provider modules for
the journal + pre-flight units.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


# --------------------------------------------------------------------------- #
# CLI argument wiring
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("argv", [["--until", "recon"], ["--yes"], ["--provider", "claude"]])
def test_supervised_only_flags_require_supervised(argv):
    import nightly
    with pytest.raises(SystemExit):
        nightly.main(argv)


def test_until_choices_validated():
    import nightly
    with pytest.raises(SystemExit):
        nightly.main(["--supervised", "--until", "bogus-stage"])


# --------------------------------------------------------------------------- #
# Hypothesize-stage failure detection (hb-a2w)
# --------------------------------------------------------------------------- #

def test_hypothesize_failures_since_filters_to_transient_failure_types(monkeypatch, tmp_path):
    """Only the two infra/transient event types count as failures; the four reasoned-drop
    types (out-of-scope/invalid/divergence/version-unresolved) must be ignored."""
    import nightly
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")

    before = len(ledger_mod.read_all())
    ledger_mod.append_event("hypothesis-out-of-scope", slug="a", target="t", resolved="r")
    ledger_mod.append_event("hypothesis-llm-unavailable", slug="prog-x", asset="pkg-b")
    ledger_mod.append_event("hypothesis-invalid", slug="c", errors=[])
    ledger_mod.append_event("hypothesis-parse-error", slug="prog-x")
    ledger_mod.append_event("hypothesis-version-unresolved", slug="e", target="t")
    ledger_mod.append_event("hypothesis-target-divergence", slug="f", target="t", recon_asset="r")

    failures = nightly._hypothesize_failures_since(before)
    assert [e["event_type"] for e in failures] == [
        "hypothesis-llm-unavailable", "hypothesis-parse-error",
    ]
    assert [e["slug"] for e in failures] == ["prog-x", "prog-x"]


def test_hypothesize_failures_since_ignores_entries_before_the_marker(monkeypatch, tmp_path):
    """Entries logged before `before_count` (e.g. from an earlier run) must not be
    re-reported on a later call."""
    import nightly
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")

    ledger_mod.append_event("hypothesis-llm-unavailable", slug="prog-old", asset="pkg-old")
    marker = len(ledger_mod.read_all())
    ledger_mod.append_event("hypothesis-llm-unavailable", slug="prog-old", asset="pkg-new")

    failures = nightly._hypothesize_failures_since(marker)
    assert [e["asset"] for e in failures] == ["pkg-new"]


def test_failure_identifier_prefers_asset_over_program_slug():
    """`slug` is the program-level scope slug (constant across every recon item in a run) --
    NOT a per-item identifier. `asset` (when the event captured it) is the real per-item
    identifier and must be preferred."""
    import nightly

    assert nightly._failure_identifier(
        {"event_type": "hypothesis-llm-unavailable", "slug": "huntr-npm-x", "asset": "left-pad"}
    ) == "left-pad"
    # hypothesis-parse-error never captures `asset` (see generate.py) -- fall back to slug.
    assert nightly._failure_identifier(
        {"event_type": "hypothesis-parse-error", "slug": "huntr-npm-x"}
    ) == "huntr-npm-x"


# --------------------------------------------------------------------------- #
# Supervised flow
# --------------------------------------------------------------------------- #

def _patch_common(monkeypatch, *, scopes):
    """No-op the pre-flight and scope load; isolate side-effecting tail stages."""
    import nightly
    monkeypatch.setattr(nightly, "_preflight", lambda **kw: [])
    monkeypatch.setattr(nightly, "load_all_scopes", lambda: scopes)
    monkeypatch.setattr(nightly, "stage_briefing", lambda *a, **k: Path("briefing.md"))
    # Identity verdict reconstruction so tests can pass plain dicts through triage.
    monkeypatch.setattr(nightly, "_verdict_from_dict", lambda vd: vd)
    return nightly


def test_until_recon_stops_before_hypothesize(monkeypatch, tmp_path):
    nightly = _patch_common(monkeypatch, scopes={"huntr-npm-x": {"venue": "huntr"}})
    monkeypatch.setattr(nightly, "stage_recon", lambda scopes: [{"asset": "x"}])

    def _boom(*a, **k):
        raise AssertionError("hypothesize must not run when --until recon")
    monkeypatch.setattr(nightly, "stage_hypothesize", _boom)

    rc = nightly.run_supervised(until="recon", auto_yes=True, journals_dir=tmp_path)
    assert rc == 0
    journal = (tmp_path / next(p.name for p in tmp_path.iterdir())).read_text("utf-8")
    assert "Checkpoint — recon" in journal
    assert "stopped after recon (--until)" in journal


def test_full_run_zero_novel_is_null_result(monkeypatch, tmp_path):
    nightly = _patch_common(monkeypatch, scopes={"huntr-npm-x": {"venue": "huntr"}})
    monkeypatch.setattr(nightly, "stage_recon", lambda scopes: [{"asset": "x"}])
    monkeypatch.setattr(nightly, "stage_hypothesize", lambda scopes, recon: [{"id": "h1"}])
    monkeypatch.setattr(
        nightly, "stage_verify",
        lambda hyps: [{"program_slug": "huntr-npm-x", "verified": False, "verdict": "refuted"}],
    )
    monkeypatch.setattr(nightly, "stage_triage", lambda verdicts, slug, *, now: [])
    monkeypatch.setattr(nightly, "stage_draft_findings",
                        lambda novel, slug, *, today: ["SHOULD-NOT-RUN"] if novel else [])

    rc = nightly.run_supervised(auto_yes=True, journals_dir=tmp_path)
    assert rc == 0
    journal = (tmp_path / next(p.name for p in tmp_path.iterdir())).read_text("utf-8")
    assert "NULL result" in journal
    assert "Checkpoint — draft" in journal


def test_no_scopes_loaded_exits_2(monkeypatch, tmp_path):
    nightly = _patch_common(monkeypatch, scopes={})
    rc = nightly.run_supervised(auto_yes=True, journals_dir=tmp_path)
    assert rc == 2


def test_provider_flag_sets_env_for_all_stages(monkeypatch, tmp_path):
    """--provider must reach every stage's select_client(), which reads
    SECRESEARCH_LLM_PROVIDER — a bare param would miss the verify stage's PoC author."""
    import os
    nightly = _patch_common(monkeypatch, scopes={})  # empty -> early return, env already set
    monkeypatch.setenv("SECRESEARCH_LLM_PROVIDER", "claude")  # auto-restored at teardown
    nightly.run_supervised(auto_yes=True, provider="llama", journals_dir=tmp_path)
    assert os.environ["SECRESEARCH_LLM_PROVIDER"] == "llama"


def test_operator_abort_at_recon(monkeypatch, tmp_path):
    nightly = _patch_common(monkeypatch, scopes={"huntr-npm-x": {"venue": "huntr"}})
    monkeypatch.setattr(nightly, "stage_recon", lambda scopes: [{"asset": "x"}])
    # auto_yes=False -> halt calls _pause_for_inspection; simulate operator typing "n".
    monkeypatch.setattr(nightly, "_pause_for_inspection", lambda stage, summary: False)

    def _boom(*a, **k):
        raise AssertionError("hypothesize must not run after operator abort")
    monkeypatch.setattr(nightly, "stage_hypothesize", _boom)

    rc = nightly.run_supervised(auto_yes=False, journals_dir=tmp_path)
    assert rc == 0
    journal = (tmp_path / next(p.name for p in tmp_path.iterdir())).read_text("utf-8")
    assert "aborted at recon" in journal


# --------------------------------------------------------------------------- #
# Pre-flight (fail-loud)
# --------------------------------------------------------------------------- #

def test_preflight_fails_loud_on_bad_provider(monkeypatch):
    import nightly
    from llm.client import LLMConfigError

    class _BadClient:
        def preflight(self):
            raise LLMConfigError("no key")
    monkeypatch.setattr(nightly, "select_client", lambda provider=None: _BadClient())
    # sandbox_doctor must not even be reached.
    monkeypatch.setattr(nightly, "sandbox_doctor",
                        lambda **k: (_ for _ in ()).throw(AssertionError("reached sandbox")))
    with pytest.raises(LLMConfigError):
        nightly._preflight()


def test_preflight_fails_on_sandbox_down(monkeypatch):
    import nightly

    class _OkClient:
        def preflight(self):
            return None
    monkeypatch.setattr(nightly, "select_client", lambda provider=None: _OkClient())
    monkeypatch.setattr(nightly, "sandbox_doctor", lambda **k: (False, ["docker unreachable"]))
    with pytest.raises(RuntimeError, match="sandbox preflight failed"):
        nightly._preflight()


def test_preflight_ok(monkeypatch):
    import nightly

    class _OkClient:
        def preflight(self):
            return None
    monkeypatch.setattr(nightly, "select_client", lambda provider=None: _OkClient())
    monkeypatch.setattr(nightly, "sandbox_doctor", lambda **k: (True, ["docker reachable"]))
    assert nightly._preflight() == ["docker reachable"]


# --------------------------------------------------------------------------- #
# RunJournal unit
# --------------------------------------------------------------------------- #

def test_run_journal_incremental(tmp_path):
    from lib.journal import RunJournal

    j = RunJournal("huntr-npm-x", date="2026-06-27", journals_dir=tmp_path)
    j.start(program_reason="picked x because in-scope + tractable")
    assert j.path.exists()
    j.checkpoint("recon", outcome="reached", detail="recon items: 3")
    j.note("hb-dzu: reconciled huntr to App Router og:url existence check; ecosystem via manifest probe")
    j.finish(outcome="NULL result")

    text = j.path.read_text("utf-8")
    assert "# Run Journal — huntr-npm-x (2026-06-27)" in text
    assert "picked x because in-scope + tractable" in text
    assert "## Checkpoint — recon" in text
    assert "recon items: 3" in text
    assert "hb-dzu" in text
    assert "## Outcome" in text
    assert "NULL result" in text
    # start() then appends -> outcome section comes after the checkpoint section.
    assert text.index("Checkpoint — recon") < text.index("## Outcome")


def test_run_journal_start_clobbers(tmp_path):
    from lib.journal import RunJournal

    j = RunJournal("s", date="2026-06-27", journals_dir=tmp_path)
    j.start(program_reason="first")
    j.checkpoint("recon", outcome="reached")
    j.start(program_reason="second")  # re-start should reset the file
    text = j.path.read_text("utf-8")
    assert "second" in text
    assert "Checkpoint — recon" not in text


# --------------------------------------------------------------------------- #
# Briefing-level failure surfacing (hb-a2w) -- covers BOTH run_unattended and
# run_supervised, since both call stage_briefing.
# --------------------------------------------------------------------------- #

def test_stage_briefing_flags_hypothesize_failures(monkeypatch, tmp_path):
    import nightly
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(nightly, "RUNTIME_BRIEFINGS_DIR", tmp_path)

    before = len(ledger_mod.read_all())
    ledger_mod.append_event("hypothesis-llm-unavailable", slug="huntr-npm-x", asset="left-pad")

    path = nightly.stage_briefing({}, [], [], [], [], ledger_count_before_run=before)
    text = path.read_text("utf-8")
    assert "Hypothesize-stage failures (1)" in text
    assert "hypothesis-llm-unavailable@left-pad" in text


def test_stage_briefing_silent_when_no_failures(monkeypatch, tmp_path):
    import nightly
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(nightly, "RUNTIME_BRIEFINGS_DIR", tmp_path)

    before = len(ledger_mod.read_all())
    ledger_mod.append_event("hypothesis-out-of-scope", slug="huntr-npm-x", target="t", resolved="r")

    path = nightly.stage_briefing({}, [], [], [], [], ledger_count_before_run=before)
    text = path.read_text("utf-8")
    assert "Hypothesize-stage failures" not in text


def test_run_unattended_threads_ledger_marker_to_briefing(monkeypatch, tmp_path):
    """The cron path (run_unattended) has no journal at all -- the briefing is the only
    artifact a human reads after an unattended run, so it must carry this signal."""
    import nightly
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(nightly, "RUNTIME_BRIEFINGS_DIR", tmp_path)
    monkeypatch.setattr(nightly, "RUNTIME_SCHEDULED_RUNS", tmp_path / "scheduled-runs.jsonl")
    monkeypatch.setattr(nightly, "load_all_scopes", lambda: {})
    monkeypatch.setattr(nightly, "stage_recon", lambda scopes: [])

    def _hypothesize_with_failure(scopes, recon):
        ledger_mod.append_event("hypothesis-llm-unavailable", slug="huntr-npm-x", asset="left-pad")
        return []
    monkeypatch.setattr(nightly, "stage_hypothesize", _hypothesize_with_failure)
    monkeypatch.setattr(nightly, "stage_verify", lambda hyps: [])

    rc = nightly.run_unattended()
    assert rc == 0
    briefing_files = [p for p in tmp_path.iterdir() if p.suffix == ".md"]
    text = briefing_files[0].read_text("utf-8")
    assert "Hypothesize-stage failures (1)" in text
    assert "hypothesis-llm-unavailable@left-pad" in text
