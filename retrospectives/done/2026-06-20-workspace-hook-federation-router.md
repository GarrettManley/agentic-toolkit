# Retrospective: Workspace Hook Federation Router

**Plan:** `.claude/docs/plans/2026-06-20-workspace-hook-federation-router-plan.md`
**Commit:** `5b0cd6d` (`test(hooks): cover route_event crash-child fail-open; clarify ROOT + aggregate`) — final of 9 commits (`9e6ba28`..`5b0cd6d`)
**Tracker:** `hb-ry9` (closed)
**Date:** 2026-06-20

## Outcome

Built a parent-level Claude hook dispatcher (`.claude/hooks/hook_router.py` + `hook_router_lib.py` + `hook-router.config.json` + 26 tests), registered for all four Claude events in `.claude/settings.json`. On each event it auto-discovers depth-1 nested projects that ship their own `.claude/settings.json` (with `Duracell*`/`malachite` hard-excluded in code), and replays their matching hooks with correct per-child context (`${CLAUDE_PROJECT_DIR}` rewritten per child, single-read stdin replayed, exit codes aggregated). Net effect: `sec-research/`'s 17 governance hooks now fire from a Workspace-root session without relaunching Claude inside the subdir — the original ask — while standalone launches are unchanged. Executed subagent-driven on `master` with a per-task spec+quality review gate and a final opus whole-branch review (0 Critical, 0 Important).

## What worked

- **Defensive design upstream made the whole feature feasible.** sec-research's hooks self-locate (`__file__`-derived `WORKSPACE_ROOT`) and self-gate (`event_targets_workspace`). That let the router be **content-agnostic** — it transports events and verdicts, knows nothing about PT-1 or scopes — and federate the child with zero changes to it. A child that trusted `${CLAUDE_PROJECT_DIR}` for its own root could not have been hoisted.
- **The per-task review gate caught a real plan bug, and the fix-review caught the fix.** Task 3's review surfaced that `resolve_command` (`posix=True`) strips Windows backslashes; the fix-review then rejected the naive correction (`posix=False`, which breaks quote-stripping) in favour of keeping `posix=True` and fixing the *test* command construction. Two-stage adversarial review did exactly its job.
- **Restart-free federation proof.** Piping a crafted out-of-scope `curl` event (`tool_name=Bash`, command containing `sec-research`) through the router with `CLAUDE_PROJECT_DIR=Workspace` fired sec-research's PT-1 → `EXIT=2`; a control event → `EXIT=0`. This validated the end-to-end chain without needing a Claude restart — far higher-confidence than unit tests alone for an integration-shaped feature.
- **File-handoff + ledger kept controller context lean.** Briefs/reports/review-packages moved as files (`scripts/task-brief`, `scripts/review-package`); the `.superpowers/sdd/progress.md` ledger held durable progress across 6 tasks + reviews + a fix loop.
- **Model routing by task shape.** haiku for transcription tasks (0/1/2/4 — complete code in the brief), sonnet for integration (3/5) and per-task reviews, opus for the final whole-branch review. The opus reviewer independently re-read sec-research's `paths.py`/`common.py` to verify the child-scoping premise rather than trusting the report.

## Friction / bugs

- **`resolve_command` backslash-stripping (the load-bearing bug)**
  - *What happened:* `shlex.split(cmd, posix=True)` strips backslashes as escapes; a Windows path like `sys.executable` (`C:\...\python.exe`) became an invalid binary name → `FileNotFoundError` → fail-open (rc 0), silently masking a block.
  - *Root cause:* the plan specified `posix=True` without accounting for backslash paths; it was latent because Task 2's `run_child_hook` tests passed argv lists directly (bypassing `resolve_command`), so it only surfaced when Task 3's `route_event` spawned real subprocesses through it.
  - *How caught:* Task 3 implementer hit it during integration; Task 3 reviewer then caught that the *fix* (`posix=False`) regressed quote-handling.
  - *Fix:* keep `posix=True` (correct for the forward-slash command convention AND quoted paths); fix the tests to build commands with `Path(sys.executable).as_posix()`. Documented the forward-slash convention in `resolve_command`'s docstring.
  - *Rule:* a function that parses paths is only as correct as the path *style* its callers feed it — test it with the adversarial style (backslashes, quotes, spaces), not just the happy forward-slash case. And when a fix to a reviewed function is itself non-trivial, re-review the fix.

- **Committed `.pyc` + `git rm` blocked by the Fact-Forcing gate**
  - *What happened:* Task 0's `git add .claude/hooks/tests/` swept in `__pycache__/*.pyc`. Trying to untrack them with `git rm --cached` was hard-blocked by the Fact-Forcing safety gate (even after presenting the required disclosure).
  - *Root cause:* wholesale `git add <dir>` before a gitignore rule existed; the gate treats any `git rm` as destructive.
  - *How caught:* Task 0 review flagged the committed bytecode.
  - *Fix:* added `.claude/**/__pycache__/` + `.claude/**/*.pyc` to `.gitignore` (stops new ones); switched all subsequent task dispatches to **explicit `git add <file>` paths** (never the `tests/` dir) so tracked `.pyc` never re-stage. The two already-tracked `.pyc` remain (removal deferred to the user — gate-blocked).
  - *Rule:* gitignore generated artifacts *before* the first commit that could capture them; stage explicit files, not directories, in any repo with a destructive-command gate.

- **Plan internal inconsistency: `ROOT` derivation vs the CLI test**
  - *What happened:* the plan derived `ROOT` from `__file__`, but its own CLI smoke test set `CLAUDE_PROJECT_DIR=<tmp>` expecting "no projects" — which only holds if `ROOT` honors that env var.
  - *Root cause:* the plan author (me) didn't reconcile the test's isolation mechanism with the `ROOT` derivation.
  - *How caught:* controller pre-flight reasoning before dispatching Task 4; resolved in the dispatch by overriding to env-first (`CLAUDE_PROJECT_DIR` else `__file__`), which is also the semantically-correct source (it's the canonical project dir).
  - *Rule:* when a plan's test fixes an environment knob, the production code must read that knob — check test/impl agreement during the writing-plans self-review.

- **Indentation drift from cheap-tier implementers**
  - *What happened:* haiku implementers introduced tab-indented test functions amid a 4-space file, and mid-file imports (E402).
  - *Root cause:* transcription-tier model didn't match surrounding style; the plan's code blocks didn't pin indentation.
  - *How caught:* per-task reviews (Minor each).
  - *Rule:* acceptable cost for cheap-tier transcription; sweep style with a formatter at the end rather than re-dispatching. (Tracked as cosmetic follow-up.)

## Concrete improvements

- **Crash-path test + clarifying comments** — `5b0cd6d`, done (the one untested fail-open branch; `ROOT` env-precedence and `aggregate` reserved-param comments).
- **Publish-safe doc home** — specs/plans live under `.claude/docs/` (not `docs/superpowers/`) because the post-commit gate matches `docs/*` and would fire a Firebase deploy, and these docs name corporate repos. Pattern worth reusing for any internal-infra doc that names excluded repos.
- **Follow-up bead** (child of `hb-ry9`) — remaining: `git rm --cached` the 2 stale `.pyc` (user, gate-blocked); cosmetic test lint. Status: pending.
- **Live in-session e2e** — restart Claude at the Workspace root and trigger a sec-research-targeting action to confirm PT-1 fires live. Status: follow-up (user).
