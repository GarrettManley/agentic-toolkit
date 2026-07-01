# Discovery-Loop Validation & Stage 7 (huntr) Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Tracker:** `hb-dzz` (harness beads ledger — umbrella epic for this arc).

**Goal:** Close a live PT-2 human-approval bypass, validate `claude-cli` PoC-authoring reliability cheaply, prove the pipeline behaves correctly against one fresh target with a real scope-lifecycle safety net, and wire the one Stage 7 venue integration (huntr) that costs near-zero new code.

**Architecture:** Five sequential tasks against `sec-research/`. Task 1 closes a real, unguarded confirmation bypass shared by three scripts (blocking prerequisite for Task 5). Tasks 2 and 4 are operational — they run existing, already-wired pipeline code against real inputs rather than adding new pipeline logic. Task 3 adds a fail-safe scope-lifecycle flag so unattended cron can't silently reprocess a freshly-loaded, human-reviewed-only target. Task 5 wires huntr into the existing submission dispatcher, fixing a real status-mislabeling bug along the way.

**Tech Stack:** Python 3.12+, pytest, PyYAML, the existing sec-research hook/lib stack (`hooks/lib/paths.py`, `hooks/lib/scope_match.py`, `hooks/lib/sign_verify.py`, `hooks/lib/ledger.py`). No new dependencies.

## Global Constraints

- **Spec:** `sec-research/docs/superpowers/specs/2026-07-01-discovery-loop-validation-design.md` (companion review: `2026-07-01-discovery-loop-validation-design.review.md`). Every task below implements one numbered section of that design; do not deviate from its non-goals (§1.4): no novel-discovery capability, no `hb-5i3` provider split, no `ibb-h1`/`direct-maintainer` submission integrations, no `bugcrowd`/`intigriti`.
- **Workspace root for all commands:** `sec-research/` (the design's own convention — `python scripts/...`, `pytest`, not `python sec-research/scripts/...` from the Workspace root, unless a step says otherwise).
- **17 hook-enforced invariants apply throughout** (`sec-research/CLAUDE.md`). In particular: PT-1 (network calls must trace to a loaded scope), PT-2 (submission requires a valid approval token, **no override path**), PT-5 (PoC/registry-install commands must route through the sandbox). Task 4's live run is the only task that touches real network egress; confirm a scope is loaded before any recon step.
- **No fabrication.** A null result in Task 2 or Task 4 is a first-class, valid outcome — never strain a result to avoid one.
- **Every test file new in this plan follows the existing `tests/scripts/`-relative import convention**: `sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))` before `import <module>`, matching `tests/scripts/test_nightly_supervised.py`.
- **`sign_token()` requires the ephemeral test key** (`override_key_setup` fixture, `tests/conftest.py`) in any test that signs a real token; reuse it, do not hand-roll a second key-setup fixture.
- **Windows shell:** all example commands are POSIX-style (Git Bash / WSL); if run from PowerShell, translate `&&` chains accordingly (the pre-commit/pre-push hooks already run under Git Bash per this repo's existing hook scripts).

---

## Task 1: Close the `--test-mode-confirm` PT-2/override bypass

**Files:**
- Create: `sec-research/hooks/lib/test_mode_gate.py`
- Test: `sec-research/tests/hooks/test_test_mode_gate.py`
- Modify: `sec-research/scripts/sign_approval.py:133-134`
- Modify: `sec-research/scripts/sign_override.py:113-114`
- Test: `sec-research/tests/scripts/test_sign_override_test_mode_gate.py`
- Test: `sec-research/tests/scripts/test_sign_approval_test_mode_gate.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `lib.test_mode_gate.test_mode_confirm_allowed() -> bool` — imported by `sign_approval.py` and `sign_override.py`. Also produces hook-level enforcement in `hooks/pretooluse.py` (`check_pt2_test_mode_bypass`) as layered defense-in-depth (see Steps 17-21 below) — the env-var check alone is spoofable by anyone willing to set `PYTEST_CURRENT_TEST` themselves before a direct invocation; the hook closes that gap for any Bash-tool-issued command.

### Background

`sign_approval.py` and `sign_override.py` both define `--test-mode-confirm`, which currently sets `confirmed = True` unconditionally with zero hook coverage anywhere (confirmed: no rule in `hooks/{pretooluse,posttooluse,stop,userpromptsubmit}.py` matches invocations of either script). A token minted this way is indistinguishable from a genuine human-approved one. Fix: gate the flag behind `PYTEST_CURRENT_TEST` (set automatically by pytest in the process environment, and inherited automatically by any `subprocess.run(cmd, ...)` call that doesn't override `env=` — which is exactly how the existing tests in `tests/hooks/test_override_singleuse.py` invoke these scripts, so they need zero changes).

- [ ] **Step 1: Write the failing test for the gate function**

Create `sec-research/tests/hooks/test_test_mode_gate.py`:

```python
"""Tests for the --test-mode-confirm gate shared by sign_approval.py and sign_override.py
(design §3: closes a live, unguarded PT-2/override bypass).
"""
from __future__ import annotations


def test_returns_false_without_pytest_marker(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from lib.test_mode_gate import test_mode_confirm_allowed
    assert test_mode_confirm_allowed() is False


def test_returns_true_with_pytest_marker(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/hooks/test_test_mode_gate.py::fake")
    from lib.test_mode_gate import test_mode_confirm_allowed
    assert test_mode_confirm_allowed() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sec-research && pytest tests/hooks/test_test_mode_gate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.test_mode_gate'`

- [ ] **Step 3: Write minimal implementation**

Create `sec-research/hooks/lib/test_mode_gate.py`:

```python
"""Shared --test-mode-confirm gate for sign_approval.py and sign_override.py.

Each of those scripts has a `--test-mode-confirm` CLI flag that skips its interactive
human-typed confirmation step, so tests can invoke them non-interactively. Left
unguarded, that flag is a live bypass of the human confirmation step it exists to
protect -- a token minted via the flag is signed identically to one minted through a
genuine confirmation, and no hook anywhere enforces anything on these scripts'
invocations (see docs/superpowers/specs/2026-07-01-discovery-loop-validation-design.md
§3). This gate closes that: the flag only takes effect when PYTEST_CURRENT_TEST is
present in the environment -- a marker pytest sets automatically for the duration of a
test run, and one that subprocess.run(...) (without an explicit env= override) inherits
automatically. Outside a pytest process, the marker is absent, so the flag is refused.
"""
from __future__ import annotations

import os


def test_mode_confirm_allowed() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sec-research && pytest tests/hooks/test_test_mode_gate.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd sec-research
git add hooks/lib/test_mode_gate.py tests/hooks/test_test_mode_gate.py
git commit -m "feat(sec-research): add shared --test-mode-confirm environment gate"
```

- [ ] **Step 6: Write the failing regression test for sign_override.py**

Create `sec-research/tests/scripts/test_sign_override_test_mode_gate.py`:

```python
"""End-to-end proof that sign_override.py's --test-mode-confirm refuses to bypass the
interactive confirmation outside a pytest process (design §3)."""
from __future__ import annotations

import os
import subprocess
import sys


def _env_without_pytest_marker() -> dict:
    env = dict(os.environ)
    env.pop("PYTEST_CURRENT_TEST", None)
    return env


def test_test_mode_confirm_refused_outside_pytest(override_key_setup, clean_overrides, workspace_root):
    cmd = [
        sys.executable,
        str(workspace_root / "scripts" / "sign_override.py"),
        "--rule", "PT-1",
        "--target", "test.example.com",
        "--reason", "regression coverage for the test-mode-confirm gate itself",
        "--test-mode-confirm",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(workspace_root),
        env=_env_without_pytest_marker(), input="",
    )
    assert result.returncode == 1
    assert "only honored" in result.stderr
    signed_dir = workspace_root / "overrides" / "signed"
    assert not signed_dir.exists() or not list(signed_dir.iterdir())


def test_test_mode_confirm_still_works_under_pytest(override_key_setup, clean_overrides, workspace_root):
    """Regression: tests/hooks/test_override_singleuse.py depends on this exact CLI
    invocation succeeding via subprocess.run's default environment inheritance."""
    cmd = [
        sys.executable,
        str(workspace_root / "scripts" / "sign_override.py"),
        "--rule", "PT-1",
        "--target", "test.example.com",
        "--reason", "confirming the happy path still works under pytest",
        "--test-mode-confirm",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace_root))
    assert result.returncode == 0, f"expected success under pytest env, got: {result.stderr}"
    assert "Token signed and written" in result.stdout
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd sec-research && pytest tests/scripts/test_sign_override_test_mode_gate.py -v`
Expected: FAIL on `test_test_mode_confirm_refused_outside_pytest` (returncode is currently 0, no refusal message) — `test_test_mode_confirm_still_works_under_pytest` already passes (unmodified behavior).

- [ ] **Step 8: Implement the fix in sign_override.py**

Modify `sec-research/scripts/sign_override.py`. Add the import near the top (after the existing `lib` imports at line 25):

```python
from lib import ledger  # noqa: E402
from lib.test_mode_gate import test_mode_confirm_allowed  # noqa: E402
```

Replace lines 113-114:

```python
    if args.test_mode_confirm:
        confirmed = True
```

with:

```python
    if args.test_mode_confirm:
        if not test_mode_confirm_allowed():
            print(
                "ERROR: --test-mode-confirm is only honored when invoked under pytest "
                "(PYTEST_CURRENT_TEST not set in the environment). This flag exists to "
                "support automated tests, not to bypass the human confirmation step "
                "outside of them.",
                file=sys.stderr,
            )
            return 1
        confirmed = True
```

- [ ] **Step 9: Run tests to verify they pass, plus the existing suite for regressions**

Run: `cd sec-research && pytest tests/scripts/test_sign_override_test_mode_gate.py tests/hooks/test_override_singleuse.py -v`
Expected: all PASS (2 + 5 = 7 passed — `test_override_singleuse.py` has 5 test functions) — `test_override_singleuse.py`'s existing tests must be unaffected.

- [ ] **Step 10: Commit**

```bash
cd sec-research
git add scripts/sign_override.py tests/scripts/test_sign_override_test_mode_gate.py
git commit -m "fix(sec-research): sign_override.py refuses --test-mode-confirm outside pytest"
```

- [ ] **Step 11: Write the failing regression test for sign_approval.py**

Create `sec-research/tests/scripts/test_sign_approval_test_mode_gate.py`. This drafts a real, schema-valid finding via the existing drafter (reusing `scripts/draft/drafter.py`, the same pattern `tests/scripts/test_draft_drafter.py` uses) so `sign_approval.py`'s pre-checks pass, then calls `sign_approval.main()` in-process (monkeypatching `sys.argv` and the module's `FINDINGS_DIR`) so `monkeypatch.delenv` can control `PYTEST_CURRENT_TEST` visibility directly — no subprocess needed here, since the gate function is a pure `os.environ` read that works identically in-process.

Two things `draft.drafter` needs that the bare `scripts/` path insert doesn't provide: (1) it does fully-qualified `from scripts.draft.errors import ...`-style imports internally, which requires **WORKSPACE_ROOT itself** (the parent of `scripts/`) on `sys.path`, not just `scripts/`; sibling nightly tests get this for free because `nightly.py` self-adds WORKSPACE_ROOT before importing `draft.drafter`, but this test never imports `nightly`, so it must add WORKSPACE_ROOT explicitly. (2) `draft_findings()` calls `ledger.append_event("draft-created", ...)` internally — without isolation, every test run appends a real event to the actual, git-tracked `submissions/ledger.jsonl`; `test_draft_drafter.py` avoids this with an autouse `_isolate_ledger` fixture, reused here:

```python
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
    """draft_findings() appends a real "draft-created" ledger event; capture it instead
    of writing to the real, git-tracked submissions/ledger.jsonl (same pattern as
    tests/scripts/test_draft_drafter.py's own _isolate_ledger fixture)."""
    import scripts.draft.drafter as d
    class _Cap:
        def __init__(self): self.events = []
        def append_event(self, et, **f): self.events.append((et, f)); return {}
    monkeypatch.setattr(d, "ledger", _Cap(), raising=False)


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
```

- [ ] **Step 12: Run test to verify it fails**

Run: `cd sec-research && pytest tests/scripts/test_sign_approval_test_mode_gate.py -v`
Expected: `test_test_mode_confirm_refused_outside_pytest` FAILS (returncode 0, token gets written — the bypass is still live before Step 13); `test_test_mode_confirm_still_works_under_pytest` already PASSES (unmodified behavior).

- [ ] **Step 13: Implement the fix in sign_approval.py**

Modify `sec-research/scripts/sign_approval.py`. Add the import after the existing `lib` imports at line 29:

```python
from lib.sign_verify import sign_token  # noqa: E402
from lib import ledger  # noqa: E402
from lib.test_mode_gate import test_mode_confirm_allowed  # noqa: E402
```

Replace lines 133-134:

```python
    if args.test_mode_confirm:
        confirmed = True
```

with:

```python
    if args.test_mode_confirm:
        if not test_mode_confirm_allowed():
            print(
                "ERROR: --test-mode-confirm is only honored when invoked under pytest "
                "(PYTEST_CURRENT_TEST not set in the environment). This flag exists to "
                "support automated tests, not to bypass the human confirmation step "
                "outside of them.",
                file=sys.stderr,
            )
            return 1
        confirmed = True
```

- [ ] **Step 14: Run test to verify it passes**

Run: `cd sec-research && pytest tests/scripts/test_sign_approval_test_mode_gate.py -v`
Expected: PASS (2 passed)

- [ ] **Step 15: Run the full existing suite for this area to confirm no regressions**

Run: `cd sec-research && pytest tests/hooks/ tests/scripts/test_sign_approval_test_mode_gate.py tests/scripts/test_sign_override_test_mode_gate.py tests/scripts/test_draft_drafter.py -v`
Expected: all PASS, zero failures.

- [ ] **Step 16: Commit**

```bash
cd sec-research
git add scripts/sign_approval.py tests/scripts/test_sign_approval_test_mode_gate.py
git commit -m "fix(sec-research): sign_approval.py refuses --test-mode-confirm outside pytest"
```

### Layered defense: hook-level enforcement

The `PYTEST_CURRENT_TEST` env-var check above closes the *accidental* misuse case, but it
is a self-attested check performed by the same process being gated — anyone (including an
agent operating this workspace via the Bash tool) willing to set that ordinary,
undocumented-as-secret env var before a **direct** invocation can spoof it:
`PYTEST_CURRENT_TEST=x python scripts/sign_override.py --rule PT-1 ... --test-mode-confirm`
would pass the env-var check even though it was never run under pytest. This defeats the
actual threat model design §3 exists to close, and Task 5 wires a real external submission
dispatch on top of this same approval path. Fix: add hook-level enforcement that fires on
the literal Bash **command text** an agent writes — a legitimate `pytest tests/...`
invocation never contains `--test-mode-confirm` in that text (pytest's own internal
`subprocess.run(...)` call constructs it at runtime, invisible to the hook), so this cannot
false-positive-block the real test suite while still hard-blocking any direct
Bash-issued attempt to use the flag outside of it.

- [ ] **Step 17: Write the failing test for the hook**

Create `sec-research/tests/hooks/test_pt2_test_mode_bypass.py`:

```python
"""Tests for hook-level enforcement of the --test-mode-confirm gate (design §3, layered
defense alongside lib/test_mode_gate.py's env-var check): a Bash command that directly
invokes sign_approval.py or sign_override.py with --test-mode-confirm must be blocked
unconditionally, with no override -- an ordinary env var is not a secret, so a
self-attested check inside the gated process alone can always be spoofed.
"""
from __future__ import annotations


def _bash_event(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_direct_sign_override_invocation_with_flag_is_blocked():
    import pretooluse
    event = _bash_event(
        "python scripts/sign_override.py --rule PT-1 --target x "
        "--reason 'trying to bypass confirmation directly' --test-mode-confirm"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is not None


def test_direct_sign_approval_invocation_with_flag_is_blocked():
    import pretooluse
    event = _bash_event(
        "python scripts/sign_approval.py FIND-2026-07-01-001 --venue huntr --test-mode-confirm"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is not None


def test_spoofed_env_var_prefix_does_not_evade_the_hook():
    """The env-var spoofing attempt itself: prefixing the command with a fake
    PYTEST_CURRENT_TEST does not help, because the hook matches on the script+flag
    pair in the command text, not on any environment state."""
    import pretooluse
    event = _bash_event(
        "PYTEST_CURRENT_TEST=fake python scripts/sign_override.py --rule PT-1 "
        "--target x --reason 'spoofed env var attempt' --test-mode-confirm"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is not None


def test_pytest_invocation_itself_is_not_blocked():
    """A real pytest run's own Bash command text never contains --test-mode-confirm
    literally -- pytest's internal subprocess.run(...) call builds that argument list
    at runtime, invisible to this hook. This must NOT be blocked."""
    import pretooluse
    event = _bash_event(
        "pytest tests/scripts/test_sign_override_test_mode_gate.py "
        "tests/hooks/test_override_singleuse.py -v"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is None


def test_unrelated_command_is_not_blocked():
    import pretooluse
    event = _bash_event("git status")
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is None


def test_flag_without_a_confirmation_script_is_not_blocked():
    """--test-mode-confirm only matters in the context of sign_approval.py/
    sign_override.py -- an unrelated command that happens to contain the same
    substring (e.g. in commit-message prose) must not be blocked (avoids the
    known command-string-overmatch class of bug this workspace has hit before)."""
    import pretooluse
    event = _bash_event(
        'git commit -m "docs: mention --test-mode-confirm in a changelog entry"'
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is None
```

- [ ] **Step 18: Run test to verify it fails**

Run: `cd sec-research && pytest tests/hooks/test_pt2_test_mode_bypass.py -v`
Expected: FAIL with `AttributeError: module 'pretooluse' has no attribute 'check_pt2_test_mode_bypass'`

- [ ] **Step 19: Implement the hook check**

Modify `sec-research/hooks/pretooluse.py`. Add after the existing `SUBMIT_SCRIPT_PATTERNS`/`_command_invokes_submit_py` block (currently lines 36-44), before `_approval_token_provided`:

```python
CONFIRMATION_SCRIPT_PATTERNS = [
    r"\bscripts[\\/]sign_approval\.py\b",
    r"\bsec-research[\\/]scripts[\\/]sign_approval\.py\b",
    r"\bscripts[\\/]sign_override\.py\b",
    r"\bsec-research[\\/]scripts[\\/]sign_override\.py\b",
]


def _command_invokes_confirmation_script(cmd: str) -> bool:
    return any(re.search(p, cmd, re.IGNORECASE) for p in CONFIRMATION_SCRIPT_PATTERNS)
```

Add the check function after `check_pt2_submission` (currently ends at line 159), before `check_pt3_path`:

```python
def check_pt2_test_mode_bypass(event: dict) -> int | None:
    """PT-2 (extended): a Bash command that directly invokes sign_approval.py or
    sign_override.py with --test-mode-confirm is blocked unconditionally, no override.

    Layered defense alongside lib/test_mode_gate.py's PYTEST_CURRENT_TEST check inside
    those scripts: that env-var check correctly lets a real pytest run's own internal
    subprocess.run(...) calls through, but cannot stop something with Bash access from
    directly typing `PYTEST_CURRENT_TEST=x python scripts/sign_override.py ...
    --test-mode-confirm` -- an ordinary env var is not a secret, so a self-attested check
    inside the same process being gated can always be spoofed by whoever controls the
    invocation. This hook closes that: it fires on the literal Bash COMMAND TEXT an agent
    writes, which a legitimate `pytest ...` invocation never contains (pytest builds the
    flagged subprocess call internally, not as an agent-authored Bash command string), so
    this cannot false-positive-block the real test suite while still hard-blocking any
    direct Bash-issued attempt to use the flag outside of it. See
    docs/superpowers/specs/2026-07-01-discovery-loop-validation-design.md §3.
    """
    tool_name = event.get("tool_name", "")
    if tool_name != "Bash":
        return None
    tool_input = event.get("tool_input", {}) or {}
    cmd = tool_input.get("command", "") or ""
    if not _command_invokes_confirmation_script(cmd):
        return None
    if "--test-mode-confirm" not in cmd:
        return None
    return block(
        "PT-2",
        "sign_approval.py/sign_override.py --test-mode-confirm",
        "Direct Bash invocation of --test-mode-confirm is never allowed outside a real "
        "pytest run -- this flag exists for automated tests only, not to bypass the "
        "human confirmation step. No override path (same as PT-2 itself).",
        override_path=None,
    )
```

Then wire it into the dispatch tuple in `main()` (currently line 342):

```python
    for check in (check_pt1_scope, check_pt2_submission, check_pt2_test_mode_bypass, check_pt3_path, check_pt4_fab_refs, check_pt5_sandbox, check_pt6_secrets):
```

- [ ] **Step 20: Run test to verify it passes**

Run: `cd sec-research && pytest tests/hooks/test_pt2_test_mode_bypass.py -v`
Expected: PASS (6 passed)

- [ ] **Step 21: Run the full hooks test suite for regressions, then commit**

Run: `cd sec-research && pytest tests/hooks/ -v`
Expected: all PASS, zero failures (the new check is additive to the existing dispatch tuple and only matches a narrow, specific command shape).

```bash
cd sec-research
git add hooks/pretooluse.py tests/hooks/test_pt2_test_mode_bypass.py
git commit -m "feat(sec-research): hook-block direct --test-mode-confirm Bash invocations"
```

---

## Task 2: PoC-authoring reliability validation (design §2.1)

**Files:**
- Create: `sec-research/runtime/eval/claude-cli-track-b.json` (generated artifact, not source — `runtime/` is gitignored)
- No source changes — `scripts/eval/authoring_eval.py` already implements `--track b`, provider-agnostic via `SECRESEARCH_LLM_PROVIDER`.

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: a captured pass-rate report informing whether `claude-cli` PoC-authoring is reliable enough to trust in Task 4's live run. No code symbols consumed by later tasks — this is an operational, not code, deliverable.

### Background

This replaces the original (rejected — see review §CRITICAL) plan of re-running `nightly.py` against `minimatch`. `authoring_eval.py --track b` directly measures PoC-authoring reliability against the same fixed `minimatch`/CVE-2022-3517 fixture already used to disqualify `qwen2.5-coder-7b` (0/5 trials, `hb-26v`) — no live venue fetch, no dependency on a real program happening to be currently vulnerable. `N=5` matches `hb-26v`'s own precedent trial count for this exact harness (each trial drives a real Docker sandbox verify cycle via `LLMPocStrategy`, so cost scales with N — 5 is the established, defensible baseline, not an arbitrary pick). No pass-rate gate is imposed — per the design, the deliverable is the measurement itself, informing (not blocking) Task 4.

- [ ] **Step 1: Confirm Docker-in-WSL2 AND the claude-cli provider are both reachable (fail loud before spending an LLM/sandbox budget on a broken environment)**

Run: `cd sec-research && python scripts/sandbox/doctor.py`
Expected output: a line confirming Docker is reachable (matching the shape already proven live 2026-06-26, `docs/superpowers/runbooks/2026-06-26-docker-wsl2-install.md`). If this fails, stop and fix the Docker/WSL2 environment before proceeding — do not attempt Step 2 against a broken sandbox.

Then confirm the claude-cli provider itself is configured, using the codebase's own existing preflight check rather than discovering a misconfiguration mid-run:

```bash
python -c "
from llm.client import select_client
select_client('claude-cli').preflight()
print('claude-cli preflight OK')
"
```
Expected: prints `claude-cli preflight OK`, exit code 0. If this raises, fix the claude-cli configuration (credentials/PATH) before proceeding — an uncaught crash mid-eval is worse than a loud upfront failure.

- [ ] **Step 2: Run the eval**

Run:
```bash
cd sec-research
SECRESEARCH_LLM_PROVIDER=claude-cli python scripts/eval/authoring_eval.py --track b --trials 5 --report runtime/eval/claude-cli-track-b.json
```
Expected: prints a JSON summary to stdout including `"track_b": {"model": ..., "trials": 5, "verified": <N>, "refuted": <N>, "error": <N>, "skipped": <N>, "rate": <float>}`, and writes the same JSON to `runtime/eval/claude-cli-track-b.json`. Exit code 0. Any `rate` value is a valid, informative result — record it as-is.

- [ ] **Step 3: Verify the report artifact**

Run: `cd sec-research && python -c "import json; d = json.load(open('runtime/eval/claude-cli-track-b.json')); assert d['track_b']['trials'] == 5; print('rate:', d['track_b']['rate'])"`
Expected: prints `rate: <float>`, exit code 0 (an `AssertionError`/`KeyError` here means Step 2 did not complete cleanly — investigate before proceeding to Task 4, since Task 4 depends on knowing whether `claude-cli` PoC-authoring is trustworthy).

- [ ] **Step 4: Record the result in the plan's Execution Log**

No commit needed for this task — `runtime/` is gitignored by design (raw eval output is not source). Instead, append an entry to this plan file's **## Execution Log** section (at the end of this document, after Task 5) stating the measured rate and whether it changes Task 4's risk posture (e.g., a 0/5 rate would mean Task 4's verify checkpoint is very unlikely to produce a `TRIAGE_DUPLICATE`, making a null the expected, not surprising, outcome).

**Mid-run failure note:** each of the 5 trials is a real Docker sandbox verify cycle plus a real claude-cli call (real cost, real time). `score_track_b` does not support resuming a partial run — if Step 2 fails or is interrupted partway, simply re-run it from the top; there is no partial-progress preservation, so a retry re-incurs the full 5-trial cost. This is acceptable given the small, bounded trial count; no special resumability logic is built for this operational task.

---

## Task 3: Scope-lifecycle control — `rules.unattended_eligible` (design §2.3)

**Files:**
- Modify: `sec-research/schema/program.schema.json`
- Modify: `sec-research/scripts/nightly.py`
- Test: `sec-research/tests/scripts/test_nightly_unattended_eligible.py`
- Modify: `sec-research/docs/SCOPE_SCHEMA.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `nightly._filter_unattended_eligible(scopes: dict) -> tuple[dict, list[str]]`, a new optional `rules.unattended_eligible: bool` schema field (absent/false = not processed by the unattended cron path). Consumed by **Task 4** (which relies on this filter existing so the freshly-loaded target stays supervised-only) — **Task 4 depends on this task**.

**Scope note (adversarial review):** the original design of this task included a companion `scripts/authorize_unattended.py` script (a confirmation-gated tool to flip the flag back to `true`). Three independent reviewers converged on cutting it: nothing in this plan invokes it (Task 4 deliberately never runs it — the whole point is the target stays supervised-only), and design §2.3's actual requirement is fully satisfied by the schema field + filter alone. The flag's reverse direction (opting a reviewed scope back into cron) is a manual `scope.yaml` edit — genuinely simple and low-stakes (a single boolean, easily reviewed in a diff) — deferred to a future, separately-justified plan if and when an operator actually needs to do this routinely enough to warrant tooling.

### Background

`run_unattended()` (the already-registered, daily-3am `sec-research-nightly` scheduled task) and `run_supervised()` currently call identical stage functions with no distinction — nothing stops the cron path from silently reprocessing a freshly-loaded scope to full draft-finding completion on the very next scheduled run, with zero human checkpoint. `programs/` is currently empty, so this is a clean, non-breaking schema addition (no migration needed for existing scope files).

- [ ] **Step 1: Write the failing test for the schema field**

Add to `sec-research/schema/program.schema.json`'s `rules.properties` object (after `no_dast_against_prod`, before `embargo_period_days`) is the target of Step 3 below; first write the test that exercises it end-to-end via `nightly.py`'s filter (schema validation itself is already covered generically by `tests/schemas/test_schemas_self_validate.py`, which needs no changes since we're only adding an optional property).

Create `sec-research/tests/scripts/test_nightly_unattended_eligible.py`:

```python
"""Tests for the unattended-eligible scope filter (design §2.3): the unattended
nightly-cron path must skip any scope not explicitly marked
rules.unattended_eligible=true, so a freshly-loaded supervised-only target isn't
silently reprocessed to full draft-finding completion by the next scheduled run.
run_supervised() is NOT filtered -- an explicit --supervised invocation IS the human
supervision itself, regardless of the flag.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_filter_skips_scope_without_rules_key_at_all():
    import nightly
    eligible, skipped = nightly._filter_unattended_eligible({"fresh-target": {}})
    assert eligible == {}
    assert skipped == ["fresh-target"]


def test_filter_skips_scope_with_empty_rules():
    import nightly
    eligible, skipped = nightly._filter_unattended_eligible({"fresh-target": {"rules": {}}})
    assert eligible == {}
    assert skipped == ["fresh-target"]


def test_filter_skips_scope_with_flag_explicitly_false():
    import nightly
    scopes = {"fresh-target": {"rules": {"unattended_eligible": False}}}
    eligible, skipped = nightly._filter_unattended_eligible(scopes)
    assert eligible == {}
    assert skipped == ["fresh-target"]


def test_filter_keeps_scope_explicitly_authorized():
    import nightly
    scopes = {"reviewed-target": {"rules": {"unattended_eligible": True}}}
    eligible, skipped = nightly._filter_unattended_eligible(scopes)
    assert eligible == scopes
    assert skipped == []


def test_run_unattended_only_processes_eligible_scopes(monkeypatch, tmp_path):
    """End-to-end: run_unattended() must not call stage_recon for a scope that isn't
    unattended-eligible, and must still process one that is."""
    import nightly
    from lib import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(nightly, "RUNTIME_BRIEFINGS_DIR", tmp_path)
    monkeypatch.setattr(nightly, "RUNTIME_SCHEDULED_RUNS", tmp_path / "scheduled-runs.jsonl")
    monkeypatch.setattr(nightly, "load_all_scopes", lambda: {
        "fresh-target": {"rules": {}},
        "reviewed-target": {"rules": {"unattended_eligible": True}},
    })

    seen_scopes: dict = {}
    def _capture_recon(scopes):
        seen_scopes.update(scopes)
        return []
    monkeypatch.setattr(nightly, "stage_recon", _capture_recon)
    monkeypatch.setattr(nightly, "stage_hypothesize", lambda scopes, recon: [])
    monkeypatch.setattr(nightly, "stage_verify", lambda hyps: [])

    rc = nightly.run_unattended()
    assert rc == 0
    assert list(seen_scopes.keys()) == ["reviewed-target"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sec-research && pytest tests/scripts/test_nightly_unattended_eligible.py -v`
Expected: FAIL with `AttributeError: module 'nightly' has no attribute '_filter_unattended_eligible'`

- [ ] **Step 3: Add the schema field**

Modify `sec-research/schema/program.schema.json`. In the `rules.properties` object, after the `no_dast_against_prod` property (before `embargo_period_days`), add:

```json
        "unattended_eligible": {
          "type": "boolean",
          "description": "If true, the unattended nightly-cron path (run_unattended) may process this scope to full draft-finding completion. Absent or false: the scope is skipped by cron (still fully usable via `nightly.py --supervised`, which is unaffected by this flag). Defaults to NOT eligible so a freshly-loaded scope stays supervised-only until a human explicitly sets this to true by hand-editing scope.yaml."
        },
```

- [ ] **Step 4: Implement the filter and wire it into `run_unattended()`**

Modify `sec-research/scripts/nightly.py`. Add the new function after `stage_refresh_disclosed` (around line 125), before `stage_recon`:

```python
def _filter_unattended_eligible(scopes: dict) -> tuple[dict, list[str]]:
    """Only scopes explicitly marked rules.unattended_eligible=true are processed by the
    unattended nightly-cron path. A freshly-loaded scope (rules.unattended_eligible
    absent or false) is skipped here until a human hand-edits its scope.yaml to set
    rules.unattended_eligible: true -- this is what makes a supervised run's implicit
    "no submission in this step" boundary real rather than merely stated; without it,
    the already-registered nightly cron would silently reprocess a fresh scope to full
    draft-finding completion on the very next scheduled run. See
    docs/superpowers/specs/2026-07-01-discovery-loop-validation-design.md §2.3.

    run_supervised() is NOT filtered by this flag -- an explicit --supervised
    invocation IS the human supervision itself, regardless of the flag's value.

    Returns (eligible_scopes, skipped_slugs).
    """
    eligible: dict = {}
    skipped: list[str] = []
    for slug, scope in scopes.items():
        if (scope.get("rules") or {}).get("unattended_eligible") is True:
            eligible[slug] = scope
        else:
            skipped.append(slug)
    return eligible, skipped
```

Then modify `run_unattended()` (currently lines 247-298). Replace:

```python
    scopes = load_all_scopes()
    print(f"Loaded {len(scopes)} program scope(s)")
    ledger_count_before_run = len(ledger.read_all())
```

with:

```python
    scopes = load_all_scopes()
    total_loaded = len(scopes)
    print(f"Loaded {total_loaded} program scope(s)")
    scopes, skipped_slugs = _filter_unattended_eligible(scopes)
    if skipped_slugs:
        print(f"Skipping {len(skipped_slugs)} scope(s) not marked unattended-eligible: "
              f"{', '.join(skipped_slugs)} (hand-edit programs/<slug>/scope.yaml's "
              f"rules.unattended_eligible to true once a supervised session has "
              f"reviewed them)")
    ledger_count_before_run = len(ledger.read_all())
```

And update the run-record write near the end of `run_unattended()` (currently lines 286-296) to log what was skipped:

```python
    RUNTIME_SCHEDULED_RUNS.parent.mkdir(parents=True, exist_ok=True)
    with RUNTIME_SCHEDULED_RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "kind": "nightly",
            "started_at": started_at,
            "finished_at": finished_at,
            "scopes_loaded": total_loaded,
            "scopes_processed": len(scopes),
            "scopes_skipped_not_unattended_eligible": skipped_slugs,
            "drafts_produced": len(drafts),
            "briefing_path": str(briefing),
        }) + "\n")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sec-research && pytest tests/scripts/test_nightly_unattended_eligible.py tests/schemas/test_schemas_self_validate.py -v`
Expected: all PASS.

- [ ] **Step 6: Run the full existing nightly test suite for regressions**

Run: `cd sec-research && pytest tests/scripts/test_nightly_supervised.py tests/scripts/test_nightly_stage4b.py tests/scripts/test_nightly_stage5_6.py tests/scripts/test_nightly_stage_verify.py -v`
Expected: all PASS, zero failures — `run_supervised()` is untouched by this change.

- [ ] **Step 7: Update `docs/SCOPE_SCHEMA.md`**

Modify `sec-research/docs/SCOPE_SCHEMA.md`. Find the `rules.*` table that documents each existing rules field individually (`ai_assistance_allowed`, `ai_disclosure_required`, `rate_limit_per_min`, `user_agent_required`, `no_dast_against_prod`, `embargo_period_days`) and add a row for the new field, matching that table's existing format:

```
| `unattended_eligible` | boolean | No | If true, the unattended nightly-cron path (`nightly.py` with no `--supervised` flag) may process this scope to full draft-finding completion. Absent or false: the scope is skipped by cron (still fully usable via `nightly.py --supervised`). Defaults to NOT eligible so a freshly-loaded scope stays supervised-only until a human explicitly sets this to `true` by hand-editing `scope.yaml`. |
```

- [ ] **Step 8: Commit**

```bash
cd sec-research
git add schema/program.schema.json scripts/nightly.py tests/scripts/test_nightly_unattended_eligible.py docs/SCOPE_SCHEMA.md
git commit -m "feat(sec-research): unattended cron skips scopes not marked unattended_eligible"
```

---

## Task 4: Fresh-target pipeline-correctness proof (design §2.2)

**Depends on Task 3** (its `_filter_unattended_eligible` must already be committed to the checkout the real `sec-research-nightly` 3am cron reads before this task loads a live scope — worktree/session drift could otherwise let a fresh scope sit unprotected between this task's fetch and Task 3 landing; do not start this task until Task 3 is complete and committed, matching Task 5's explicit dependency on Task 1).

**Files:** none modified — this task is operational, driving already-wired pipeline code (Task 3's filter guarantees the loaded scope stays supervised-only afterward).

**Interfaces:**
- Consumes: `nightly._filter_unattended_eligible` (Task 3 — the loaded scope's default-false `unattended_eligible` flag is what keeps it outside cron's reach after this task; no script call is needed to achieve this, it's the field's default).
- Produces: a run journal at `runtime/journals/<slug>-2026-07-01.md` (or the date this task actually executes) and, if the target has a currently-known match, a `TRIAGE_DUPLICATE` triage record — the terminal artifact for this task either way. No code symbols consumed by later tasks.

### Background

This is the reframed, honest version of the original "novel discovery" goal (design §1.4 non-goal — the current pipeline cannot reach `TRIAGE_NOVEL` for the only implemented vuln class). Success is a correctly-deduped known result or a defensible null — **both are valid outcomes**. No submission occurs in this task.

**Target-vetting bar** (the real filter that nulled the prior `hb-322` minimatch run — its 9 advisories all targeted *transitive*, not *direct*, dependencies): the chosen program must have

1. a fetcher that succeeds (`fetch_program.py --venue huntr|ghsa --identifier <id>` returns `ok=True`),
2. recon that resolves at least one **package-typed** asset with a **committed lockfile** (closure resolution is lockfile-gated; a `package.json` with no `package-lock.json` stays ineligible regardless of this plan's other changes),
3. at least one known OSV/GHSA advisory on a **direct** dependency edge (not a transitive one), unfixed at the resolved version — **checked manually** (see Step 2's note: `scripts/recon/deps.py`'s `Closure.direct` field is hard-coded to `[]` in v1 and cannot answer this automatically),
4. `rules.ai_assistance_allowed == true` in the fetched scope.

Finding a candidate meeting all four is real vetting effort — expect several trial `fetch_program.py`/`recon_program.py` rounds against candidates before one qualifies. This is not scriptable in advance; the steps below are the *procedure*, not a fixed target. **Candidate sourcing:** start from huntr.com's active-bounty program listing (`https://huntr.com/bounties/`, browsed manually) or a GHSA advisory search filtered to `npm` ecosystem, unfixed status — either is a valid source of candidate identifiers to feed into the loop below. **Stop condition:** after **5** consecutive failed candidates (fails Step 1 or Step 2's bar), halt the loop and ask the human operator for direction rather than continuing indefinitely.

- [ ] **Step 1: Candidate vetting loop**

For a huntr candidate `<owner>/<pkg>`:

```bash
cd sec-research
python scripts/fetch_program.py --venue huntr --identifier <owner>/<pkg>
```

For a GHSA candidate (advisory id form `GHSA-xxxx-xxxx-xxxx`):

```bash
python scripts/fetch_program.py --venue ghsa --identifier GHSA-xxxx-xxxx-xxxx
```

Expected (either venue): `ok: true` and a `programs/<slug>/scope.yaml` written. If `ok: false`, discard the candidate (count it toward the 5-failure stop condition above) and try the next.

Then inspect the fetched scope's `rules.ai_assistance_allowed` — if `false`, discard (counts toward the stop condition) and try the next candidate (do not proceed past this check for a disallowed program).

- [ ] **Step 2: Recon the candidate and check the vetting bar**

```bash
python scripts/recon_program.py --slug <slug>
```

Expected: writes `runtime/recon/<slug>/recon.json`. Inspect it: at least one asset with `asset_type: package` and a non-empty `known_advisories` list.

**Direct-vs-transitive check is manual, not automated:** `scripts/recon/deps.py`'s `Closure.direct` field is hard-coded to `[]` in v1 ("v1 does not distinguish direct from transitive deps") — `recon.json` cannot answer this question on its own. Instead, open the cloned repo's own `package.json` (under the recon working directory the closure resolution used) and check whether the advisory's affected package name appears literally in its top-level `"dependencies"` or `"devDependencies"` object — if it only appears nested inside `package-lock.json`'s dependency tree under a *different* top-level package, it is transitive; discard the candidate. Cross-check the advisory record's `fixed` field (not `fixed_version` — `scripts/recon/advisories.py`'s `Advisory` dataclass names it `fixed`) is a version greater than the currently resolved one. If no candidate asset meets this bar, discard the candidate (counts toward the 5-failure stop condition) and return to Step 1 with a new candidate.

**Once a candidate passes this bar and is carried forward to Step 3, remove every other, previously-rejected candidate's scope directory** (`rm -rf programs/<rejected-slug>/`) before proceeding. This is required, not optional: `nightly.py --supervised` calls `load_all_scopes()` with **no slug filter** and picks `slug = next(iter(scopes))` — an arbitrary (in practice, first-inserted) entry. Leftover rejected scopes would silently contaminate Step 3, potentially running the pipeline against the wrong target.

- [ ] **Step 3: Run the supervised pipeline against the vetted target**

```bash
python scripts/nightly.py --supervised --provider claude-cli
```

(`--provider claude-cli`, not `claude` — matching the exact provider Task 2 measured; running a different provider here would mean Task 2's reliability measurement never informed the provider actually used.)

Run **interactively** (respond `y` at each halt) rather than passing `--yes` — the whole point of this task is human supervision of a live, network-touching, real-cost run; only use `--yes` if the operator has already reviewed the target thoroughly across Steps 1-2 and is confident skipping the live checkpoints is safe. Expected: stage-by-stage checkpoints print to stdout. Terminal outcome is either:
- `DRAFT path` with N finding(s) — inspect `findings/<trace-id>/finding.md` and its `verification.json`; this may or may not be `TRIAGE_DUPLICATE` depending on how deduplication resolves given the loaded advisory data, or
- `NULL result` — a defensible null with the full hypothesis audit trail in the printed journal path.

Both are valid, complete outcomes per design §1.3. **Do not** run `sign_approval.py` or `submit.py` in this task — no submission occurs here.

**Mid-run failure note:** this is a human-supervised, re-runnable-from-the-top operation — if the process crashes or is interrupted mid-pipeline, simply re-run Step 3; `nightly.py`'s own journal/checkpoint design (already built, not part of this plan) lets you inspect exactly how far a prior attempt got before restarting. No additional resumability logic is built for this task.

- [ ] **Step 4: Confirm the scope stays supervised-only**

```bash
python -c "
import yaml
from pathlib import Path
scope = yaml.safe_load(Path('programs/<slug>/scope.yaml').read_text())
assert scope.get('rules', {}).get('unattended_eligible') is not True, 'scope must NOT be unattended-eligible yet'
print('confirmed: scope stays supervised-only')
"
```

Expected: prints `confirmed: scope stays supervised-only`, exit code 0. (There is no `authorize_unattended.py` script in this plan — see Task 3's scope note — so there is nothing to refrain from running here beyond not hand-editing `scope.yaml`'s flag, which this task does not do.)

- [ ] **Step 5: Record the outcome**

No source commit needed (the run journal lives under gitignored `runtime/`). Append an entry to this plan file's **## Execution Log** section (at the end of this document, after Task 5) — target chosen, draft vs. null, journal path. This is the proof artifact for design §1.3 step 2's definition of done.

---

## Task 5: Stage 7 huntr wiring (design §2.4)

**Depends on Task 1** (the PT-2 bypass fix is a stated blocking prerequisite in the design — do not start this task until Task 1 is complete and committed).

**Files:**
- Modify: `sec-research/scripts/submit.py:1-11,268-271,336-354`
- Test: `sec-research/tests/scripts/test_submit_huntr_dispatch.py`
- Modify: `sec-research/docs/SUBMISSION_GATE.md`
- Modify: `sec-research/CLAUDE.md`

**Interfaces:**
- Consumes: nothing new from Tasks 2-4.
- Produces: `submit._select_dispatcher(venue: str) -> tuple[callable, bool]`, `submit._status_for_dispatch(is_manual_alias: bool) -> str`.

### Background

`huntr.com` has no public API (`scripts/fetchers/huntr.py`'s own docstring confirms `api.huntr.com` does not resolve) — its fetched scope already self-declares `submission.protocol: "manual-form"`. `--venue huntr` should dispatch through the exact same function `--venue manual-form` already uses. The existing status-derivation line (`new_status = "submitted-manual" if args.venue == "manual-form" else "submitted"`) is keyed on the venue string, not on which dispatch function ran — naively adding a `elif args.venue == "huntr":` branch that calls `_dispatch_manual_form` while keeping `venue="huntr"` would fall to the `else` branch and stamp a false, fully-confirmed `"submitted"` status. Fix: extract the dispatch selection and status derivation into two small, directly-testable pure functions.

- [ ] **Step 1: Write the failing tests**

Create `sec-research/tests/scripts/test_submit_huntr_dispatch.py`:

```python
"""Tests for Stage 7 huntr venue wiring (design §2.4): huntr aliases to the
manual-form dispatcher, but the resulting finding/ledger status must reflect that
only a human-completed manual hand-off occurred -- never a false, fully-confirmed
'submitted'.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_select_dispatcher_huntr_aliases_to_manual_form():
    import submit
    fn, is_manual = submit._select_dispatcher("huntr")
    assert fn is submit._dispatch_manual_form
    assert is_manual is True


def test_select_dispatcher_manual_form_itself():
    import submit
    fn, is_manual = submit._select_dispatcher("manual-form")
    assert fn is submit._dispatch_manual_form
    assert is_manual is True


def test_select_dispatcher_ghsa_is_not_manual_alias():
    import submit
    fn, is_manual = submit._select_dispatcher("ghsa")
    assert fn is submit._dispatch_ghsa
    assert is_manual is False


def test_select_dispatcher_unknown_venue_stubs():
    import submit
    fn, is_manual = submit._select_dispatcher("ibb-h1")
    ok, info = fn("FIND-2026-07-01-001", Path("."), {})
    assert ok is False
    assert is_manual is False


def test_status_for_dispatch_manual_alias_is_submitted_manual():
    import submit
    assert submit._status_for_dispatch(True) == "submitted-manual"


def test_status_for_dispatch_real_confirmed_is_submitted():
    import submit
    assert submit._status_for_dispatch(False) == "submitted"


def test_huntr_never_produces_bare_submitted_status():
    """Regression guard for the exact bug found in adversarial review: huntr must
    never reach the fully-confirmed 'submitted' status through this path."""
    import submit
    _, is_manual = submit._select_dispatcher("huntr")
    assert submit._status_for_dispatch(is_manual) == "submitted-manual"


def test_main_huntr_end_to_end_yields_submitted_manual_status(
    override_key_setup, clean_overrides, tmp_path, monkeypatch,
):
    """End-to-end coverage of main() itself (not just the pure-function units above,
    which is all this file otherwise covers) -- submit.py currently has zero test
    coverage before this plan, and main()'s actual PT-2 token-consumption + ledger
    + finding-status-write logic is the substance of a human-gated submission script
    this workspace's CLAUDE.md calls load-bearing. Exercises the full --venue huntr
    path with a real, validly-signed approval token."""
    import json
    import sys
    from datetime import datetime, timedelta, timezone
    import submit
    from lib.sign_verify import sign_token

    trace_id = "FIND-2026-07-01-001"
    finding_dir = tmp_path / trace_id
    finding_dir.mkdir()
    (finding_dir / "finding.md").write_text(
        "---\n"
        "trace_id: FIND-2026-07-01-001\n"
        "program_slug: huntr-npm-test-target\n"
        "status: ready-for-review\n"
        "---\n"
        "Finding body.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(submit, "FINDINGS_DIR", tmp_path)
    monkeypatch.setattr(submit, "SUBMISSIONS_TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(submit, "OVERRIDES_USED_DIR", tmp_path / "overrides-used")
    monkeypatch.setattr(submit, "_load_program_scope", lambda slug: {
        "submission": {"protocol": "manual-form", "endpoint": "https://huntr.com/repos/x/y"},
    })
    monkeypatch.setattr(submit, "_dispatch_manual_form",
                        lambda trace_id, finding_dir, scope_data: (True, "submitted-manual"))

    events: list[tuple[str, dict]] = []
    class _Cap:
        def append_event(self, et, **f):
            events.append((et, f)); return {}
    monkeypatch.setattr(submit, "ledger", _Cap(), raising=False)

    now = datetime.now(timezone.utc)
    payload = {
        "token_id": "apv-2026-07-01-001",
        "trace_id": trace_id,
        "venue": "huntr",
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_uses": 1,
    }
    payload["signature"] = sign_token(payload)
    submit.SUBMISSIONS_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    (submit.SUBMISSIONS_TOKENS_DIR / "apv-2026-07-01-001.json").write_text(
        json.dumps(payload), encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", [
        "submit.py", "--trace", trace_id, "--token", "apv-2026-07-01-001", "--venue", "huntr",
    ])
    rc = submit.main()
    assert rc == 0

    updated = (finding_dir / "finding.md").read_text(encoding="utf-8")
    assert "status: submitted-manual" in updated
    assert "status: submitted\n" not in updated

    event_types = [et for et, _ in events]
    assert "submission-attempted" in event_types
    assert "submission-succeeded" in event_types
    succeeded = next(f for et, f in events if et == "submission-succeeded")
    assert succeeded["outcome"] == "submitted-manual"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sec-research && pytest tests/scripts/test_submit_huntr_dispatch.py -v`
Expected: FAIL with `AttributeError: module 'submit' has no attribute '_select_dispatcher'` (the new `test_main_huntr_end_to_end_...` test also fails here, for the same reason — `_select_dispatcher` doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

Modify `sec-research/scripts/submit.py`. First, update the module docstring (lines 1-11) — huntr moves out of the stubbed list:

```python
"""submit.py — submission gate dispatcher.

PT-2 hook validates --token before this runs. This script dispatches per --venue:
  --venue manual-form  : opens browser to submission URL, copies finding-body,
                         marks finding submitted-manual; exits with reminder.
  --venue ghsa         : uses `gh api` POST to repo's security-advisories endpoint
                         (full implementation in Stage 1).
  --venue huntr        : aliases to the manual-form dispatcher above (huntr has no
                         public API to integrate against; ledger records venue="huntr"
                         for accurate audit).
  --venue ibb-h1|h1|bugcrowd|intigriti|direct-maintainer : stubbed in Stage 1.

Every dispatch (full or stubbed) appends to submissions/ledger.jsonl.
"""
```

Update `STAGE_1_FULL` (currently line 31) to include huntr, documenting dispatch-completeness state in-code:

```python
STAGE_1_FULL = {"manual-form", "ghsa", "huntr"}
```

Add these two functions after `_dispatch_stub` (currently lines 268-271), before `_load_program_scope`:

```python
def _select_dispatcher(venue: str):
    """Return (dispatch_fn, is_manual_alias) for the given venue.

    huntr has no public submission API (scripts/fetchers/huntr.py's own fetched scope
    self-declares submission.protocol="manual-form") -- it reuses the manual-form
    dispatcher directly rather than a fake API integration. is_manual_alias
    distinguishes this from a real confirmed submission for status derivation (see
    _status_for_dispatch below); see
    docs/superpowers/specs/2026-07-01-discovery-loop-validation-design.md §2.4.
    """
    if venue in ("manual-form", "huntr"):
        return _dispatch_manual_form, True
    if venue == "ghsa":
        return _dispatch_ghsa, False
    return (lambda trace_id, finding_dir, scope_data: _dispatch_stub(venue, trace_id)), False


def _status_for_dispatch(is_manual_alias: bool) -> str:
    """Status must reflect which dispatch function actually ran, not the venue string
    -- keying off venue alone would stamp huntr (or any future manual-form alias) with
    a false, fully-confirmed "submitted" even though only the manual browser+clipboard
    hand-off occurred, with no way to verify the human actually completed the paste."""
    return "submitted-manual" if is_manual_alias else "submitted"
```

Then replace the dispatch block in `main()` (currently lines 335-345):

```python
    # Dispatch
    if args.venue == "manual-form":
        ok, info = _dispatch_manual_form(args.trace, finding_dir, scope_data)
    elif args.venue == "ghsa":
        ok, info = _dispatch_ghsa(args.trace, finding_dir, scope_data)
    else:
        ok, info = _dispatch_stub(args.venue, args.trace)

    if ok:
        new_status = "submitted-manual" if args.venue == "manual-form" else "submitted"
        _update_finding_status(finding_dir, new_status, venue_response=info)
```

with:

```python
    # Dispatch
    dispatch_fn, is_manual_alias = _select_dispatcher(args.venue)
    ok, info = dispatch_fn(args.trace, finding_dir, scope_data)

    if ok:
        new_status = _status_for_dispatch(is_manual_alias)
        _update_finding_status(finding_dir, new_status, venue_response=info)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sec-research && pytest tests/scripts/test_submit_huntr_dispatch.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Run the broader test suite for regressions**

Run: `cd sec-research && pytest tests/ -q`
Expected: all tests pass (matches the ledger-verified `470 passed, 6 skipped` baseline from the `hb-7hf` landing, plus this plan's new tests — an increased pass count, zero new failures).

- [ ] **Step 6: Update `docs/SUBMISSION_GATE.md`**

Modify `sec-research/docs/SUBMISSION_GATE.md`. Move `huntr` out of the "Stage 7 — Will be filled in (currently stubbed)" table into the "Stage 1 — Full implementations" table, as an alias row:

```
| `huntr` | Aliases to the `manual-form` behavior above (huntr.com has no public submission API — `scripts/fetchers/huntr.py` confirms `api.huntr.com` does not resolve). Ledger records `venue="huntr"` (not `manual-form`) for accurate per-venue audit history. |
```

and remove the `huntr` row from the Stage 7 stub table below it.

- [ ] **Step 7: Update `sec-research/CLAUDE.md`**

Modify `sec-research/CLAUDE.md`'s "Stage 1 vs Stages 2-7" section (auto-loaded every session in this workspace). Find the sentence "Still pending: venue-specific submission integrations beyond GHSA + manual-form (Stage 7)" and update it to reflect huntr now being wired:

```
Still pending: venue-specific submission integrations beyond GHSA, manual-form, and huntr
(aliased to manual-form) (Stage 7) — ibb-h1 and direct-maintainer remain stubbed, and —
crucially — autonomous discovery of a *novel* finding has NOT been demonstrated
end-to-end...
```

(Preserve the rest of that sentence and paragraph verbatim; only the "Still pending" clause changes.)

- [ ] **Step 8: Commit**

```bash
cd sec-research
git add scripts/submit.py tests/scripts/test_submit_huntr_dispatch.py docs/SUBMISSION_GATE.md CLAUDE.md
git commit -m "feat(sec-research): wire --venue huntr through the manual-form dispatcher"
```

---

## Verification (whole-plan)

- [ ] Full suite green: `cd sec-research && pytest tests/ -q` — record actual pass/skip counts and exit code. If the suite regresses at this late point (after five tasks' worth of commits have already landed), isolate the responsible commit via `git bisect` across this plan's own commit range, or re-run each task's own test file individually per its own Step N to narrow it down before investigating further.
- [ ] Task 1's bypass fix does not regress `tests/hooks/test_override_singleuse.py` (explicitly re-run in Step 9/15), and the layered hook enforcement (Steps 17-21) does not false-positive-block a real `pytest ...` invocation (explicitly re-run in Step 21).
- [ ] Task 2's report file exists at `runtime/eval/claude-cli-track-b.json` with a valid `track_b.rate` (any value); the result is recorded in the Execution Log below.
- [ ] Task 3's filter is proven both at the unit level (`_filter_unattended_eligible`) and end-to-end (`run_unattended` only touches eligible scopes) — both covered in Step 5/6.
- [ ] Task 4's target satisfies all four vetting-bar criteria (including the manual direct-vs-transitive check) before the supervised run is trusted as a real correctness proof, rejected candidate scopes are removed before the final run, `--provider claude-cli` is used (not `claude`), and the loaded scope is confirmed to remain `unattended_eligible != true` afterward (Step 4); the outcome is recorded in the Execution Log below.
- [ ] Task 5's regression guard (`test_huntr_never_produces_bare_submitted_status`) passes, closing the exact bug found in adversarial review, and the new end-to-end `main()` test passes.
- [ ] No task touches `ibb-h1`, `direct-maintainer`, `bugcrowd`, `intigriti`, or `hb-5i3` — confirm via one `git diff --stat` across this plan's full commit range (from before Task 1's first commit to after Task 5's last) that it touches only the files listed across all five tasks' **Files** blocks.

---

## Execution Log

Append entries here as Tasks 2 and 4 (the two operational, non-code tasks) actually run —
this is the one concrete location both tasks' recording steps point at, per adversarial
review (an unresolved "progress trail... or the retrospective" either/or was flagged and
fixed to point here specifically).

**Task 2 (PoC-authoring reliability):** _not yet run — append the measured `track_b.rate`,
trial breakdown, and whether it changes Task 4's risk posture here once Task 2 executes._

**Task 4 (fresh-target correctness proof):** _not yet run — append the target chosen (venue
+ identifier), draft-vs-null outcome, and the run journal path here once Task 4 executes._
