# Retrospective: Harness Quick-Wins Cluster — hb-tfh / hb-2ni / hb-4a4 / hb-5cj

**Plan:** `~/.claude/plans/let-s-create-a-plan-happy-porcupine.md`
**Commit:** `a61729d` (`fix(aether): migrate eval-run skill + classifier agent to llama-server`)
**Date:** 2026-06-26 _(transcribed from the in-plan retrospective; executed 2026-06-25)_

## Outcome

A batch of four small, independently-shippable harness fixes across three locations. All four beads resolved: **hb-tfh** (stale recovery-pending flag — live, 29/29 tests), **hb-4a4** (stray `strict` profile — diagnosis), and **hb-5cj** (aether eval-artifact Ollama→llama-server migration — committed `claude-marketplace@a61729d`) are done and closed; **hb-2ni** (deferred Stop-hook TS typecheck for aether-engine) is implemented + verified in the working tree with its commit deferred (open, noted). Follow-up `hb-esr` filed for the broader plugin Ollama surface.

## What worked

- **Pre-execution adversarial review paid for itself.** It caught that hb-2ni's `additionalContext` surfacing was infeasible on a Stop hook (→ `decision:block` block-once), that hb-tfh's gate-time regeneration was over-built and fail-open (→ a 2-file write-path fix at the real defect, `session_recovery_start.py:156-161`), and that hb-5cj was an Ollama→llama-server migration with fictional artifacts, not a token swap.
- **Re-verifying every load-bearing claim against ground truth** repeatedly corrected stale beads — the `eval:run` / `eval-runner.ts` / `ollama.ts` / "38 tests" references were all wrong in the bead text itself.
- **TDD on hb-tfh** — the stale-flag test failed `True is not false` exactly as the bug predicted, then went green.

## Friction / bugs

- **hb-4a4 was a no-op**
  - *What happened:* No stray `DISCIPLINE_HOOK_PROFILE` env var exists anywhere (User/Machine/process); steady-state already resolves to `standard`.
  - *Root cause:* The 2026-06-19 `strict` firing was an ephemeral shell-export / parallel-session artifact, not a persistent var.
  - *Fix:* Diagnosis was the whole deliverable; no pin applied (a global pin would have silenced sec-research's hard-block edit-gate).
  - *Rule (generalizable):* For "remove a stray config" tasks, diagnose persistence first — a pin over a non-existent var is a behavior-neutral edit that can carry blast radius.

- **aether-engine commit blocked by missing `node_modules`**
  - *What happened:* The hb-2ni commit couldn't land — husky pre-commit can't run without deps.
  - *Root cause:* Fresh/clean working copy without `npm install`; not anticipated in the plan.
  - *Fix:* Deferred the commit rather than bypassing with `--no-verify`.
  - *Rule:* Don't `--no-verify` past a missing-toolchain failure — defer the commit and record the exact remaining step.

- **`~/.claude` recovery hooks are untracked**
  - *What happened:* hb-tfh ships live (hooks run from the working files) with no commit.
  - *Root cause:* The `~/.claude/hooks/` files are untracked-not-ignored — un-anticipated but benign.
  - *Rule:* Confirm whether a target dir is git-tracked before planning a "commit the fix" step.

- **marketplace `verify.sh` required regenerating `docs/skill-index.md`** after the skill-description change — caught by the gate, fixed, re-verified green. *Rule:* a skill-description edit implies a skill-index regen; the gate enforces it.

## Concrete improvements

- **hb-tfh** — `summarize_sentinel` formatter + unconditional stale-flag clear in `session_recovery_start.py` (live, 29/29 tests). Done.
- **hb-5cj** — eval-run SKILL.md + classifier-regression-checker agent migrated to llama-server; aether 1.1.1 + changelogs (`a61729d`). Done.
- **hb-4a4** — diagnosed, no pin (correct outcome). Done.
- **hb-2ni** — `mark_ts_dirty.mjs` + `deferred_typecheck.mjs` + `.gitignore` re-include fix, implemented & verified; **commit deferred** (needs `npm install` + branch + one-time hook-trust approval). Open, user-owned.
- **hb-esr** — follow-up bead filed for the full-plugin Ollama→llama-server sweep.
