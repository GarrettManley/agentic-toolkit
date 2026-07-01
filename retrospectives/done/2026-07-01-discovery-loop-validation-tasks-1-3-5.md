# Retrospective: Discovery-Loop Validation & Stage 7 (huntr) Wiring — Tasks 1, 3, 5

**Plan:** `sec-research/docs/superpowers/plans/2026-07-01-discovery-loop-validation-plan.md`
**Commit:** `ced26ec` (`docs(sec-research): record completion-gate evidence for the Tasks 1/3/5 delivery`)
**Date:** 2026-07-01
**Tracker:** `hb-dzz` (stays open — Tasks 2/4 remain)

## Outcome

Closed a live, unguarded PT-2 human-approval bypass (`--test-mode-confirm`) with layered
defense (env-var gate + hook enforcement), added a fail-safe scope-lifecycle filter so
unattended nightly cron can't silently reprocess a freshly-loaded scope, and wired huntr
into Stage 7 submission (aliased to the existing manual-form dispatcher, fixing a real
status-mislabeling bug along the way). 12 commits landed to `master` via ff-only merge;
test suite grew from 470 to 496 passing (6 skipped throughout), zero regressions. Two
tasks from the original 5-task plan (PoC-authoring reliability validation; a live
fresh-target pipeline run) were deliberately deferred to a separate human-supervised
session — both spend real external cost and involve live judgment calls the design itself
scoped as supervised, not automated.

## What worked

- **Full deliver lifecycle in one session, each gate catching something real.** Design → adversarial design review → plan → adversarial plan review → subagent-driven execution → final whole-branch review → land, run back-to-back, each stage genuinely found and fixed defects the prior stage missed — not ceremony. The design review caught a factually-wrong revalidation target (the plan would have re-run a known-safe null and validated nothing). The plan review caught a vetting criterion referencing a `recon.json` field that's hard-coded empty in the actual code — the exact "structural incapability" failure class that had already burned a prior cycle (`hb-322`). The task review caught a real, demonstrated ledger-isolation bug in code the plan itself had specified verbatim. The final whole-branch review caught a documentation-completeness gap in a workspace where the hook map is explicitly load-bearing.
- **9-agent adversarial plan review (6 dimensions + 3 archetypes) at FULL posture.** Triaged to FULL because Effort and Complexity both scored HIGH (5 tasks, 13 files, a schema change, real external side effects). Worth the cost: three independent reviewers (scope-cut dimension, plan-scope-cutter archetype, plan-skeptic archetype) converged unprompted on the same conclusion — cut a speculative `authorize_unattended.py` script nothing in the plan actually invoked — which is a much stronger signal than any single reviewer's opinion.
- **Verifying subagent claims independently, not trusting reports.** Task 5's reviewer was explicitly instructed to re-verify the ledger-isolation claim given Task 1's identical-shaped bug had just been found — it independently re-ran the test twice and hashed the ledger file itself rather than accepting the implementer's self-report. This is what actually caught Task 1's bug in the first place (a task reviewer treating "I verified isolation" as an unverified claim, not a fact).
- **Widening a fix beyond its original scope when the evidence demands it.** The Task 1 fix dispatch asked for one specific repair (repoint an import); the fix subagent discovered the prescribed fix was necessary but not sufficient (`sign_approval.py` leaked ledger events through a second, independent path) and correctly widened the fix to patch the canonical shared object instead of chasing per-module bindings. The re-review independently confirmed this was the right call, not scope creep.
- **Deferring the two costly/live tasks explicitly rather than executing them under implicit momentum.** "Approve, proceed to Phase B execution" did not mean "also spend real API/Docker cost and touch a live external target autonomously" — scoping the subagent-driven-development dispatch to just the safe, local, code-only tasks (1/3/5) and pausing before the operational ones matched the plan's own explicit design intent (Task 4 was scoped as human-supervised from the design phase onward).

## Friction / bugs

- **Ledger-isolation fixture patched the wrong module object**
  - *What happened:* A new test (`test_sign_approval_test_mode_gate.py`) needed to isolate ledger writes during test runs. The plan's own Step 11 code added both `WORKSPACE_ROOT` and `WORKSPACE_ROOT/scripts` to `sys.path`, then imported the same underlying file two different ways in two different functions in the same test file (`scripts.draft.drafter` vs `draft.drafter`).
  - *Root cause:* Python treats those two import spellings as **distinct module objects** when both path prefixes are importable — `import scripts.draft.drafter as m1; import draft.drafter as m2; m1 is m2` is `False`. The isolation fixture patched one module's `ledger` attribute; the actual code path used the other, unpatched one. `sign_approval.main()` compounded this with a third, independent `from lib import ledger` binding of its own that neither the original fix attempt nor a naive "just fix the drafter import" patch would have caught.
  - *How caught:* The task reviewer didn't trust the implementer's self-review checkbox claiming isolation was correct — it independently ran `import scripts.draft.drafter as m1; import draft.drafter as m2; m1 is m2` and got `False`, then found the exact test-fixture data already present in the real `submissions/ledger.jsonl` (proof the bug wasn't theoretical).
  - *Fix:* Patch the canonical `lib.ledger.append_event` directly via `monkeypatch.setattr(ledger_module, "append_event", ...)` — every caller resolves through that one shared module object regardless of which import spelling brought in the calling code. Verified by running the test twice and diffing the ledger file (byte-identical both times).
  - *Rule (if generalizable):* When a test needs to monkeypatch a module-level dependency, and the test file's own `sys.path` setup makes more than one import path resolvable to "the same" underlying file, patch the **canonical, singly-resolvable** shared dependency (here, `lib.ledger`, since `hooks/lib/` has exactly one location on the path) rather than a per-caller local binding — chasing every caller's own import spelling is fragile and easy to miss one.

- **New hard-block hook rule had an untested cwd-relative evasion path**
  - *What happened:* Task 1 added `CONFIRMATION_SCRIPT_PATTERNS` to `hooks/pretooluse.py`, matching Bash command text against `scripts/sign_approval.py` / `scripts/sign_override.py` (with path prefixes). A command like `cd scripts && python sign_override.py ... --test-mode-confirm` never matched, since the script is referenced by bare filename once the cwd has already changed.
  - *Root cause:* The pattern list was path-qualified only, following the pre-existing `SUBMIT_SCRIPT_PATTERNS` convention exactly — which has the identical, still-unfixed gap (confirmed by the task reviewer, explicitly left out of scope since it predates this work).
  - *How caught:* Task review, reasoning about the hook's own claimed guarantee ("cannot be trivially evaded") against what the regex actually matched.
  - *Fix:* Added bare-filename pattern variants (`\bsign_approval\.py\b`, `\bsign_override\.py\b`) alongside the path-qualified ones. Safe against the known command-string-overmatch class of bug this workspace has hit before, because the hook also requires `--test-mode-confirm` literally in the same command string — a bare filename mention alone never blocks.
  - *Rule (if generalizable):* A Bash-command-text hook pattern that requires a path prefix is trivially defeated by a `cd` first. If a hook's own docstring or the task's framing claims "cannot be evaded," that claim needs its own explicit test for the cwd-relative case, not just the direct-invocation case.

## Concrete improvements

- **`hooks/lib/test_mode_gate.py`** — shared `test_mode_confirm_allowed()` gate, closes the `--test-mode-confirm` PT-2 bypass. Done, landed.
- **`hooks/pretooluse.py`'s `check_pt2_test_mode_bypass`** — hook-level enforcement, layered defense alongside the env-var gate. Done, landed, documented in `docs/HOOK_CONTRACTS.md` and `CLAUDE.md`'s hook map (added during the final whole-branch review's fix wave — the original plan omitted this doc step).
- **`rules.unattended_eligible` scope-lifecycle flag** — done, landed. Fail-safe default (absent/false = cron skips) independently verified against the absent-`rules`-key edge case, not just presence-with-default.
- **`submit.py`'s `_select_dispatcher`/`_status_for_dispatch`** — huntr wired to Stage 7, status-derivation bug fixed. Done, landed.
- **`docs/SCOPE_SCHEMA.md`'s stale `huntr-api` example** — fixed alongside the hook-doc gap (final review, Minor severity but directly contradicted Task 5's own established reality).
- **Follow-up, not done, deliberately deferred:** Tasks 2 (claude-cli PoC-authoring reliability eval, N=5 trials against the known minimatch fixture) and 4 (a live, human-supervised pipeline run against a freshly-vetted real target). Both require real external cost and live judgment; tracked under `hb-dzz`, which stays open until they land or are explicitly cut.
- **Known, pre-existing, out-of-scope gap surfaced but not fixed:** `SUBMIT_SCRIPT_PATTERNS`/`check_pt2_submission` has the identical bare-filename cwd-evasion gap as the one just fixed for `CONFIRMATION_SCRIPT_PATTERNS` — noted by the task reviewer as a worthwhile future fix, not addressed here since it predates and is outside this task's scope.
