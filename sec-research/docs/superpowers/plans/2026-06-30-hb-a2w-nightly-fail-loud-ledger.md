# hb-a2w: Surface Hypothesize-Stage LLM Failures Loudly (Both Entry Points)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Problem:** `generate_hypotheses` (Stage 4b) has six silent-drop paths to `submissions/ledger.jsonl`; two of them (`hypothesis-llm-unavailable`, `hypothesis-parse-error`) are transient/infra failures, not reasoned decisions — but they produce the exact same terminal "zero hypotheses for this item" shape as the other four legitimate reasoned drops. hb-322's first live run hit this for real: a masked failure (an inherited MCP tool burning the only allowed CLI turn) was indistinguishable from a genuine reasoned null until a final whole-branch code review flagged that the "trustworthy null" claim wasn't evidenced against the ledger. Today nothing surfaces this signal — an operator (or nobody, for the unattended cron path) has to know to manually grep the ledger.

**Goal:** Make both `nightly.py` entry points — the unattended cron path (`run_unattended`, the one actually registered as the `sec-research-nightly` Scheduled Task and invoked nightly with zero flags by `run_nightly.ps1`) and the manual `--supervised` path — surface any `hypothesis-llm-unavailable`/`hypothesis-parse-error` ledger event from the run, so a transient LLM failure can no longer masquerade as a reasoned zero-hypotheses null.

**Architecture:** Two layers, each with a distinct, named consumer:

1. **Shared layer (`stage_briefing`):** both entry points already call this once, at the end of the run, to write `runtime/briefings/<date>.md` — the one artifact a human is guaranteed to read after an *unattended* run (there's no journal in `run_unattended` at all, and nobody watches its stdout live). Extend it to query the ledger for the two transient-failure event types logged since the run started, and add a clearly flagged section when any are found. This is the fix for the cron path — the actual nightly production path — and it's a smaller diff than threading a new mechanism through `run_unattended` from scratch, since `stage_briefing` already has the "Ledger health" section as a natural home.
2. **Supervised-only layer (`run_supervised`'s hypothesize checkpoint):** the briefing is written only once, at the very end of the whole pipeline — by the time it's read, a supervised operator may have already clicked past several interactive checkpoints. Keep a second, real-time signal at the hypothesize checkpoint itself: a stderr `WARNING` line (shown even at the live `_pause_for_inspection` prompt) and a journal checkpoint `outcome` of `"reached-with-warnings"` instead of `"reached"` (grep-able in the run journal afterward). This preserves the original hb-a2w ask for the interactive case.

Both layers reuse one helper, `_hypothesize_failures_since(before_count)`, and one ledger-count snapshot taken once per run (`ledger_count_before_run`, captured before `stage_recon`) — no second counter needed, since no stage other than hypothesize ever appends either failure event type.

**Tech Stack:** Python 3, pytest, the existing `lib.ledger` / `lib.journal` modules in `sec-research/hooks/lib/`.

## Global Constraints

- Bug bounty target class / evidence discipline (sec-research/CLAUDE.md) does not apply — this change touches no `findings/`, no network calls, no scope files.
- Tests must never write to the real `submissions/ledger.jsonl`. Any test that calls `ledger.append_event` MUST first monkeypatch `lib.ledger.LEDGER_PATH` (imported into `ledger.py`'s own module namespace via `from .paths import LEDGER_PATH, SUBMISSIONS_DIR` — patch the `ledger` module's attribute directly, not `lib.paths.LEDGER_PATH`, or the patch won't take effect) to a path under `tmp_path`.
- The four reasoned-drop event types (`hypothesis-target-divergence`, `hypothesis-version-unresolved`, `hypothesis-invalid`, `hypothesis-out-of-scope`) must NOT trigger either layer's warning — they are correct, by-design silent drops, not failures.
- **Accepted gap, out of scope:** `generate_hypotheses`'s own docstring states `ScopeViolation` propagates uncaught. If a later recon item raises after earlier items already logged a transient failure, the whole stage aborts before either layer's failure-surfacing code runs, so those earlier failures go unsurfaced for that run (though they remain permanently in the ledger for manual `ledger_query.py` inspection). Hardening `generate_hypotheses` itself to flush/report failures incrementally is a larger, separate change to a function this plan explicitly does not touch (see below) — not in scope here.
- Existing tests in `tests/scripts/test_nightly_supervised.py` and any `run_unattended` tests must keep passing unmodified — they don't patch `LEDGER_PATH`, but since `stage_hypothesize` is always monkeypatched to a function that never calls `ledger.append_event`, the new `_hypothesize_failures_since` call in those tests will read 0 new entries against the real (unpatched) ledger and detect no failures. This is read-only and safe.
- No change to `generate_hypotheses` itself (`scripts/llm/generate.py`) — this plan only makes an already-logged signal visible, on both entry points, after their existing call to it.
- Lands by direct commit to `master` (project convention — `sec-research/` has no PR workflow). The change is additive everywhere (new optional kwarg with a default, new markdown section only rendered when failures exist, new journal outcome string only used on the failure path) and fully `git revert`-able with no partial-state cleanup needed, since nothing here writes new persistent state beyond the briefing markdown (which is regenerated, not appended, on every run).
- The Workspace root's `check_verify_before_commit.py` gate **does not fire** for these commits — it explicitly skips when every staged path is under `sec-research/`, and `.git/hooks/` currently has no installed `pre-commit`/`commit-msg` script, so `sec-research/`'s own git hooks are also inert in this repo state today. The `pytest -q` runs in Tasks 1-3 are the only real pre-land check; the Workspace gate scripts are run manually in Task 3 as a defense-in-depth supplement, not as a stand-in for an automatic gate that isn't actually active.

---

## File Structure

- Modify: `sec-research/scripts/nightly.py` — add `HYPOTHESIZE_FAILURE_EVENTS` + `_hypothesize_failures_since()` + `_failure_identifier()` helpers near the other module-level helpers (after `_today()`, lines 81-82); extend `stage_briefing()` (lines 151-187) with an optional `ledger_count_before_run` kwarg and a new briefing section; thread `ledger_count_before_run` through `run_unattended()` (lines 190-239) and `run_supervised()` (lines 275-361); modify the nested `_halt()` closure inside `run_supervised` to accept an `outcome` override; modify the Stage 4b hypothesize block inside `run_supervised` to surface failures live.
- Modify: `sec-research/tests/scripts/test_nightly_supervised.py` — add a unit-test section for the two new helpers, plus integration tests for both the briefing-section behavior and the live checkpoint behavior.

## Task 1: Helpers — `_hypothesize_failures_since` and `_failure_identifier` (pure functions, unit-tested)

**Files:**
- Modify: `sec-research/scripts/nightly.py` (insert after `_today()`, lines 81-82, before `def stage_refresh_scopes` at line 85)
- Test: `sec-research/tests/scripts/test_nightly_supervised.py` (new section, after the CLI-argument-wiring tests, before the `_patch_common` helper)

**Interfaces:**
- Produces: `HYPOTHESIZE_FAILURE_EVENTS: set[str]`, `_hypothesize_failures_since(before_count: int) -> list[dict]`, `_failure_identifier(event: dict) -> str` — all three consumed by Task 2 (`stage_briefing`) and Task 3 (`run_supervised`'s checkpoint).

- [ ] **Step 1: Confirm the current suite is green before changing anything**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest -q`
Expected: all tests pass (439 passed, 6 skipped, as of 2026-06-30 — record whatever the actual baseline count is so later steps can diff against it).

- [ ] **Step 2: Write the failing unit tests**

Add to `tests/scripts/test_nightly_supervised.py`, after `test_until_choices_validated` and before the `_patch_common` helper (i.e. as a new section between "CLI argument wiring" and "Supervised flow"):

```python
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
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest tests/scripts/test_nightly_supervised.py -k "hypothesize_failures_since or failure_identifier" -v`
Expected: all three FAIL with `AttributeError: module 'nightly' has no attribute ...`.

- [ ] **Step 4: Implement the helpers**

In `scripts/nightly.py`, insert after the `_today()` function (lines 81-82) and before `def stage_refresh_scopes` (line 85):

```python
HYPOTHESIZE_FAILURE_EVENTS = {"hypothesis-llm-unavailable", "hypothesis-parse-error"}


def _hypothesize_failures_since(before_count: int) -> list[dict]:
    """Ledger entries appended since `before_count` whose event_type is a transient/infra
    hypothesize-stage failure (LLM unreachable or its response unparseable) -- NOT a reasoned
    drop (out-of-scope/invalid/target-divergence/version-unresolved), which stays silent by
    design.

    A 'clean' zero-hypotheses outcome is only defensible if every per-item drop was a reasoned
    decision; a transient failure produces the exact same terminal shape. hb-322's first live
    run discovered this masking pattern for real (see
    docs/superpowers/research/2026-06-30-hb-322-first-real-run.md) -- this is the generalized
    fix for the swallow-and-continue architecture in generate_hypotheses, covering both the
    unattended cron path and the supervised path's live checkpoint.
    """
    return [e for e in ledger.read_all()[before_count:]
            if e.get("event_type") in HYPOTHESIZE_FAILURE_EVENTS]


def _failure_identifier(event: dict) -> str:
    """Best available per-recon-item identifier for a hypothesize-stage failure event.

    `slug` on these events is the program-level scope slug (set once per program; see
    scripts/recon/recon_item.py), constant across every recon item/asset in the run -- NOT a
    per-item identifier. `asset` (captured for hypothesis-llm-unavailable, see generate.py)
    names the actual failing recon item and must be preferred when present; fall back to
    `slug` only for event types that don't capture it (hypothesis-parse-error).
    """
    return event.get("asset") or event["slug"]
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest tests/scripts/test_nightly_supervised.py -k "hypothesize_failures_since or failure_identifier" -v`
Expected: all three PASS.

- [ ] **Step 6: Run the full suite to confirm no regressions**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest -q`
Expected: all tests pass (Step 1's baseline count plus the 3 new ones).

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Garre/Workspace
git add sec-research/scripts/nightly.py sec-research/tests/scripts/test_nightly_supervised.py
git commit -m "feat(sec-research): Add hypothesize-stage ledger failure-detection helpers (hb-a2w)"
```

## Task 2: Surface failures in `stage_briefing` — fixes the unattended/cron path

**Files:**
- Modify: `sec-research/scripts/nightly.py:151-187` (`stage_briefing`)
- Modify: `sec-research/scripts/nightly.py:190-239` (`run_unattended` — capture and thread `ledger_count_before_run`)
- Modify: `sec-research/scripts/nightly.py:275-361` (`run_supervised` — capture `ledger_count_before_run` once, before recon; thread it to its own `stage_briefing` call at the end; Task 3 reuses the same variable for the live checkpoint)
- Test: `sec-research/tests/scripts/test_nightly_supervised.py` (new tests)

**Interfaces:**
- Consumes: `HYPOTHESIZE_FAILURE_EVENTS`, `_hypothesize_failures_since(before_count: int) -> list[dict]`, `_failure_identifier(event: dict) -> str` from Task 1.
- Produces: `stage_briefing(scopes, recon, hypotheses, verified, drafts, *, ledger_count_before_run: int = 0) -> Path` (was `stage_briefing(scopes, recon, hypotheses, verified, drafts) -> Path`) — the new kwarg defaults to `0`, so any caller that doesn't pass it (there are none left after this task, but the default keeps the signature backward-compatible) behaves as if every ledger entry in the file is "this run's," which is the safest default for an unscoped caller (over-reports rather than silently hides failures).

- [ ] **Step 1: Write the failing tests**

Add to `tests/scripts/test_nightly_supervised.py`:

```python
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
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest tests/scripts/test_nightly_supervised.py -k "stage_briefing or run_unattended" -v`
Expected: all three FAIL — the first two with `TypeError: stage_briefing() got an unexpected keyword argument 'ledger_count_before_run'`; the third with the same `TypeError` once `run_unattended` is reached (or an `AssertionError` if it's reached before the kwarg error, depending on where pytest's traceback lands — either way, a failure, not a pass).

- [ ] **Step 3: Implement `stage_briefing`'s new section**

In `scripts/nightly.py`, replace the current `stage_briefing` function:

```python
def stage_briefing(scopes: dict, recon: list, hypotheses: list, verified: list, drafts: list) -> Path:
    """Always-on. Writes runtime/briefings/<date>.md with summary."""
    today = _today()
    briefing_path = RUNTIME_BRIEFINGS_DIR / f"{today}.md"
    RUNTIME_BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    body = f"""# Morning Briefing — {today}

Generated: {_utc_now_iso()}
Pipeline: Stages 3-6 wired; sandbox+verify harness proven live on real Docker (2026-06-26)

## Loaded program scopes ({len(scopes)})
"""
    for slug, scope in scopes.items():
        body += f"- `{slug}` ({scope.get('venue', '?')}): "
        body += f"{len(scope.get('in_scope', []))} in-scope, "
        body += f"{len(scope.get('out_of_scope', []))} out-of-scope\n"

    body += f"""
## Pipeline summary
- Recon items: {len(recon)}
- Hypotheses generated: {len(hypotheses)}
- Verified candidates: {sum(1 for v in verified if v.get('verified'))}
- Findings drafted: {len(drafts)} (trace-ids: {', '.join(drafts) if drafts else 'none'})

## Action items
- A run produces findings only when a program scope is loaded AND hypotheses verify novel
  (known-CVE verdicts dedup to true-negatives by design).
- Next: autonomous discovery of a novel finding against a real loaded program.

## Ledger health
- Total entries: {len(ledger.read_all())}
- Recent: see `submissions/ledger.jsonl`
"""

    briefing_path.write_text(body, encoding="utf-8")
    return briefing_path
```

with:

```python
def stage_briefing(scopes: dict, recon: list, hypotheses: list, verified: list, drafts: list,
                   *, ledger_count_before_run: int = 0) -> Path:
    """Always-on. Writes runtime/briefings/<date>.md with summary.

    ``ledger_count_before_run`` (a ledger.read_all() length snapshot taken before stage_recon)
    surfaces hb-a2w's hypothesize-stage transient-failure detection for BOTH entry points --
    run_unattended (cron, no journal at all -- this briefing is the only artifact a human is
    guaranteed to read) and run_supervised (which also gets a live stderr/journal warning at
    its hypothesize checkpoint; see the Stage 4b block in run_supervised).
    """
    today = _today()
    briefing_path = RUNTIME_BRIEFINGS_DIR / f"{today}.md"
    RUNTIME_BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    hyp_failures = _hypothesize_failures_since(ledger_count_before_run)

    body = f"""# Morning Briefing — {today}

Generated: {_utc_now_iso()}
Pipeline: Stages 3-6 wired; sandbox+verify harness proven live on real Docker (2026-06-26)

## Loaded program scopes ({len(scopes)})
"""
    for slug, scope in scopes.items():
        body += f"- `{slug}` ({scope.get('venue', '?')}): "
        body += f"{len(scope.get('in_scope', []))} in-scope, "
        body += f"{len(scope.get('out_of_scope', []))} out-of-scope\n"

    body += f"""
## Pipeline summary
- Recon items: {len(recon)}
- Hypotheses generated: {len(hypotheses)}
- Verified candidates: {sum(1 for v in verified if v.get('verified'))}
- Findings drafted: {len(drafts)} (trace-ids: {', '.join(drafts) if drafts else 'none'})

## Action items
- A run produces findings only when a program scope is loaded AND hypotheses verify novel
  (known-CVE verdicts dedup to true-negatives by design).
- Next: autonomous discovery of a novel finding against a real loaded program.
"""

    if hyp_failures:
        failure_desc = ", ".join(
            f"{e.get('event_type')}@{_failure_identifier(e)} ({e['entry_id']})"
            for e in hyp_failures
        )
        body += f"""
## Hypothesize-stage failures ({len(hyp_failures)})
This run logged {len(hyp_failures)} transient LLM failure(s) during hypothesis generation
(LLM-unavailable or unparseable response) -- NOT reasoned zero-hypotheses drops. Any null
result above may be partly or wholly a masked failure rather than a genuine reasoned
decision: {failure_desc}
"""

    body += f"""
## Ledger health
- Total entries: {len(ledger.read_all())}
- Recent: see `submissions/ledger.jsonl`
"""

    briefing_path.write_text(body, encoding="utf-8")
    return briefing_path
```

- [ ] **Step 4: Thread `ledger_count_before_run` through `run_unattended`**

Change the start of `run_unattended` (currently lines 190-196):

```python
def run_unattended() -> int:
    """Default nightly path: run the whole pipeline end-to-end with no halts (cron)."""
    started_at = _utc_now_iso()
    print(f"=== nightly.py started at {started_at} ===")

    scopes = load_all_scopes()
    print(f"Loaded {len(scopes)} program scope(s)")
```

to:

```python
def run_unattended() -> int:
    """Default nightly path: run the whole pipeline end-to-end with no halts (cron)."""
    started_at = _utc_now_iso()
    print(f"=== nightly.py started at {started_at} ===")

    scopes = load_all_scopes()
    print(f"Loaded {len(scopes)} program scope(s)")
    ledger_count_before_run = len(ledger.read_all())
```

and change the `stage_briefing` call (currently line 221):

```python
    briefing = stage_briefing(scopes, recon, hypotheses, verified, drafts)
```

to:

```python
    briefing = stage_briefing(scopes, recon, hypotheses, verified, drafts,
                              ledger_count_before_run=ledger_count_before_run)
```

- [ ] **Step 5: Thread `ledger_count_before_run` through `run_supervised`**

In `run_supervised`, change the Stage 3 recon block (currently):

```python
    # Stage 3 — recon
    recon = stage_recon(scopes)
```

to:

```python
    # Stage 3 — recon
    ledger_count_before_run = len(ledger.read_all())
    recon = stage_recon(scopes)
```

and change the final `stage_briefing` call (currently):

```python
    briefing = stage_briefing(scopes, recon, hypotheses, verified, all_drafts)
```

to:

```python
    briefing = stage_briefing(scopes, recon, hypotheses, verified, all_drafts,
                              ledger_count_before_run=ledger_count_before_run)
```

- [ ] **Step 6: Run the new tests to verify they pass**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest tests/scripts/test_nightly_supervised.py -k "stage_briefing or run_unattended" -v`
Expected: all three PASS.

- [ ] **Step 7: Run the full suite to confirm no regressions**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest -q`
Expected: all tests pass, including every pre-existing `test_nightly_supervised.py` test unmodified.

- [ ] **Step 8: Commit**

```bash
cd C:/Users/Garre/Workspace
git add sec-research/scripts/nightly.py sec-research/tests/scripts/test_nightly_supervised.py
git commit -m "fix(sec-research): Surface hypothesize-stage LLM failures in the nightly briefing for both entry points (hb-a2w)"
```

## Task 3: Live checkpoint warning in `run_supervised` (preserves the original interactive ask)

**Files:**
- Modify: `sec-research/scripts/nightly.py:303-305` (the nested `_halt` closure inside `run_supervised`)
- Modify: `sec-research/scripts/nightly.py:319-324` (the Stage 4b hypothesize block inside `run_supervised`)
- Test: `sec-research/tests/scripts/test_nightly_supervised.py` (new tests in the "Supervised flow" section)

**Interfaces:**
- Consumes: `_hypothesize_failures_since`, `_failure_identifier` (Task 1); the `ledger_count_before_run` variable now captured at the top of `run_supervised`'s Stage 3 block (Task 2, Step 5) — Task 3 reuses it directly, no new counter.
- Produces: `_halt(stage: str, summary: str, *, outcome: str = "reached") -> bool` (was `_halt(stage: str, summary: str) -> bool`) — the four other `_halt(...)` call sites in `run_supervised` (recon: line 314, verify: line 329, triage: line 344, draft: line 353) keep calling it positionally with two args, which still works since `outcome` defaults to `"reached"`.

- [ ] **Step 1: Write the failing integration tests**

Add to `tests/scripts/test_nightly_supervised.py`, in the "Supervised flow" section, after `test_until_recon_stops_before_hypothesize`:

```python
def test_hypothesize_stage_surfaces_llm_failures_loudly(monkeypatch, tmp_path, capsys):
    """A transient LLM failure during hypothesize must show up in stderr AND in the
    journal's checkpoint outcome -- live, at the checkpoint itself, not just in the
    end-of-run briefing (Task 2 already covers that for the unattended path)."""
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")

    nightly = _patch_common(monkeypatch, scopes={"huntr-npm-x": {"venue": "huntr"}})
    monkeypatch.setattr(nightly, "stage_recon", lambda scopes: [{"asset": "x"}])

    def _hypothesize_with_failure(scopes, recon):
        ledger_mod.append_event("hypothesis-llm-unavailable", slug="huntr-npm-x", asset="left-pad")
        return []
    monkeypatch.setattr(nightly, "stage_hypothesize", _hypothesize_with_failure)
    monkeypatch.setattr(nightly, "stage_verify", lambda hyps: [])
    monkeypatch.setattr(nightly, "stage_triage", lambda verdicts, slug, *, now: [])
    monkeypatch.setattr(nightly, "stage_draft_findings", lambda novel, slug, *, today: [])

    rc = nightly.run_supervised(auto_yes=True, journals_dir=tmp_path)
    assert rc == 0

    journal_files = [p for p in tmp_path.iterdir() if p.suffix == ".md"]
    journal = journal_files[0].read_text("utf-8")
    assert "reached-with-warnings" in journal
    assert "hypothesis-llm-unavailable@left-pad" in journal

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "hypothesis-llm-unavailable@left-pad" in captured.err


def test_hypothesize_stage_silent_on_reasoned_drops_only(monkeypatch, tmp_path, capsys):
    """A run whose only ledger events are reasoned drops (e.g. out-of-scope) must NOT
    trigger the warning -- it's a legitimate by-design null, not a masked failure."""
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")

    nightly = _patch_common(monkeypatch, scopes={"huntr-npm-x": {"venue": "huntr"}})
    monkeypatch.setattr(nightly, "stage_recon", lambda scopes: [{"asset": "x"}])

    def _hypothesize_with_reasoned_drop(scopes, recon):
        ledger_mod.append_event("hypothesis-out-of-scope", slug="huntr-npm-x", target="y", resolved="z")
        return []
    monkeypatch.setattr(nightly, "stage_hypothesize", _hypothesize_with_reasoned_drop)
    monkeypatch.setattr(nightly, "stage_verify", lambda hyps: [])
    monkeypatch.setattr(nightly, "stage_triage", lambda verdicts, slug, *, now: [])
    monkeypatch.setattr(nightly, "stage_draft_findings", lambda novel, slug, *, today: [])

    rc = nightly.run_supervised(auto_yes=True, journals_dir=tmp_path)
    assert rc == 0

    journal_files = [p for p in tmp_path.iterdir() if p.suffix == ".md"]
    journal = journal_files[0].read_text("utf-8")
    assert "reached-with-warnings" not in journal
    assert "## Checkpoint — hypothesize" in journal
    assert "\n- Outcome: reached\n" in journal

    captured = capsys.readouterr()
    assert "WARNING" not in captured.err
```

Note: both tests filter `tmp_path.iterdir()` by `.suffix == ".md"` rather than taking the single file like the older tests do — `tmp_path` now also holds `ledger.jsonl` (the monkeypatched `LEDGER_PATH`), so the old `next(p.name for p in tmp_path.iterdir())` pattern would non-deterministically pick either file.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest tests/scripts/test_nightly_supervised.py -k "surfaces_llm_failures_loudly or silent_on_reasoned_drops" -v`
Expected: `test_hypothesize_stage_surfaces_llm_failures_loudly` FAILS on `assert "reached-with-warnings" in journal` (still just `"reached"` today). `test_hypothesize_stage_silent_on_reasoned_drops_only` should already pass — run both together to confirm only the first genuinely fails before implementing.

- [ ] **Step 3: Implement the wiring**

In `scripts/nightly.py`, change the nested `_halt` closure (currently):

```python
    def _halt(stage: str, summary: str) -> bool:
        journal.checkpoint(stage, outcome="reached", detail=summary)
        return True if auto_yes else _pause_for_inspection(stage, summary)
```

to:

```python
    def _halt(stage: str, summary: str, *, outcome: str = "reached") -> bool:
        journal.checkpoint(stage, outcome=outcome, detail=summary)
        return True if auto_yes else _pause_for_inspection(stage, summary)
```

Then change the Stage 4b block (currently):

```python
    # Stage 4b — hypothesis
    hypotheses = stage_hypothesize(scopes, recon)
    if not _halt("hypothesize", f"hypotheses generated: {len(hypotheses)}"):
        return _stop("aborted at hypothesize")
    if until == "hypothesize":
        return _stop("stopped after hypothesize (--until)")
```

to:

```python
    # Stage 4b — hypothesis
    hypotheses = stage_hypothesize(scopes, recon)
    hyp_failures = _hypothesize_failures_since(ledger_count_before_run)
    hyp_summary = f"hypotheses generated: {len(hypotheses)}"
    hyp_outcome = "reached"
    if hyp_failures:
        failure_desc = ", ".join(
            f"{e.get('event_type')}@{_failure_identifier(e)} ({e['entry_id']})"
            for e in hyp_failures
        )
        warning = (f"WARNING: {len(hyp_failures)} hypothesize-stage LLM failure(s) "
                   f"(transient, not a reasoned drop): {failure_desc}")
        print(f"[nightly] {warning}", file=sys.stderr)
        hyp_summary += f"\n\n{warning}"
        hyp_outcome = "reached-with-warnings"
    if not _halt("hypothesize", hyp_summary, outcome=hyp_outcome):
        return _stop("aborted at hypothesize")
    if until == "hypothesize":
        return _stop("stopped after hypothesize (--until)")
```

(`ledger_count_before_run` here is the same variable captured in Task 2 Step 5, immediately before `stage_recon` — not a new snapshot.)

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest tests/scripts/test_nightly_supervised.py -k "surfaces_llm_failures_loudly or silent_on_reasoned_drops" -v`
Expected: both PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `cd C:/Users/Garre/Workspace/sec-research && pytest -q`
Expected: all tests pass, including every pre-existing `test_nightly_supervised.py` test (`test_until_recon_stops_before_hypothesize`, `test_full_run_zero_novel_is_null_result`, `test_no_scopes_loaded_exits_2`, `test_provider_flag_sets_env_for_all_stages`, `test_operator_abort_at_recon`, the three pre-flight tests, the two `RunJournal` unit tests) unmodified.

- [ ] **Step 6: Run the Workspace verification gate manually (defense-in-depth; does not auto-fire for this commit — see Global Constraints)**

Run: `cd C:/Users/Garre/Workspace && pwsh -File _scripts/pre_commit_audit.ps1 && pwsh -File _scripts/verify_workspace.ps1`
Expected: both exit 0.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Garre/Workspace
git add sec-research/scripts/nightly.py sec-research/tests/scripts/test_nightly_supervised.py
git commit -m "feat(sec-research): nightly.py --supervised surfaces hypothesize failures live at the checkpoint (hb-a2w)"
```

---

## Verification

After all three tasks land: `cd C:/Users/Garre/Workspace/sec-research && pytest -q` is green end-to-end, and the full goal is provably met by three independent tests exercising the three places a human (or nobody, for cron) would learn about a masked failure — `test_stage_briefing_flags_hypothesize_failures` (the briefing file, read by a human after `run_unattended`), `test_run_unattended_threads_ledger_marker_to_briefing` (the actual cron entry point end-to-end), and `test_hypothesize_stage_surfaces_llm_failures_loudly` (the live supervised checkpoint). All three also have a paired negative test proving reasoned drops stay silent.

## Retrospective

_(To be completed post-execution via `/plan-retrospective` — not filled in at plan-write time per the project's retrospective convention.)_

---

## Self-Review

**Spec coverage:**
- "fail loud... if a supervised run logged any hypothesis-llm-unavailable/parse-error ledger event" → Task 3 Step 3 (live checkpoint, preserves the bead's literal ask for the manual mode).
- Adversarial review's CRITICAL finding that the actual nightly cron path (`run_unattended`, confirmed via `Get-ScheduledTask` to be a live, `Ready`-state Windows Scheduled Task) had zero protection → Task 2 (shared `stage_briefing` fix), which is the higher-value half of this plan since it's the path that actually runs unattended every night.
- Adversarial review's CRITICAL finding that `slug` is the program-level slug, not a per-item identifier → `_failure_identifier()` (Task 1), prefers `asset` and is used by both Task 2 and Task 3's failure-description text, with a dedicated test (`test_failure_identifier_prefers_asset_over_program_slug`) and an asset-bearing fixture value (`"left-pad"`, distinct from the program slug `"huntr-npm-x"`) used throughout the other new tests precisely so a regression back to slug-only reporting would be caught.
- "not necessarily abort -- a partial-coverage null is still informative" → confirmed: `_halt` still returns its normal continue/abort value based on `auto_yes`/operator input in Task 3; `run_unattended`'s exit code (`return 0`) is unchanged in Task 2. The warning never changes control flow in either entry point, only visibility.
- Four reasoned-drop event types must stay silent → covered by `HYPOTHESIZE_FAILURE_EVENTS` being a 2-element allowlist, tested in both `test_hypothesize_failures_since_filters_to_transient_failure_types` and `test_stage_briefing_silent_when_no_failures`/`test_hypothesize_stage_silent_on_reasoned_drops_only`.
- Mid-stage-exception gap → explicitly named as an accepted, out-of-scope limitation in Global Constraints, per the adversarial review's ask to either test or document it.
- Missing `## Retrospective` section → added above.
- Verify-gate inaccuracy → corrected in Global Constraints and Task 3 Step 6's heading.
- "Five other `_halt` call sites" → corrected to "four" throughout.
- Pre-plan-brief rule "test must patch the ledger path, never write the real ledger" → every new test that calls `ledger_mod.append_event` first monkeypatches `LEDGER_PATH`.
- Pre-plan-brief rule "tests must use realistic ledger fixture rows, not empty lists, and assert on parsed shape" → all new tests assert on real appended rows with both `event_type` and the resolved identifier, not an empty-list stand-in.

**Placeholder scan:** none — every step has literal, complete code, exact file paths, and exact pytest invocations with expected outcomes.

**Type consistency:** `_hypothesize_failures_since(before_count: int) -> list[dict]` and `_failure_identifier(event: dict) -> str` are defined once in Task 1 and consumed with those exact names/signatures in Tasks 2 and 3; `stage_briefing`'s new `ledger_count_before_run` kwarg defaults to `0` so no caller can be left passing the old 5-positional-arg form incorrectly; `_halt`'s new `outcome` kwarg defaults to `"reached"` so the four untouched call sites compile and behave identically to before.
