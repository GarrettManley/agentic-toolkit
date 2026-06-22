# Retrospective: Session crash-recovery protocol

**Plan:** `~/.claude/plans/stateful-mixing-pinwheel.md`
**Commit:** `23530eb..8100015` (recovery output; the protocol itself is live config under `~/.claude`, gitignored)
**Date:** 2026-06-22
**Tracker:** Closes hb-bam

## Outcome

Built a durable, repeatable session-recovery protocol and applied it once to clean up the
fallout of two sessions that died (error + terminal-close). The protocol is four user-level
lifecycle hooks plus a tested pure core (`_recovery_lib.py`) and a `/recover` triage skill:
a per-session sentinel is removed by SessionEnd on a clean exit, and the next SessionStart
flags any sentinel that survived with a stale transcript or dead pid **and** at-risk state
in its cwd — injecting a recovery report and hard-gating new work until `/recover` clears
it. 24 tests pass. The one-time recovery committed the at-risk hw-dashboard (70 files),
settled the docs frontmatter churn, and closed out 10 stranded plan retrospectives — the
Workspace tree is clean.

## What worked

- **Verifying the hook lifecycle before designing** — a `claude-code-guide` agent confirmed
  `SessionEnd` is best-effort (never fires on crash/SIGKILL) and that every payload carries
  `session_id`/`transcript_path`. That turned transcript-mtime staleness into the primary
  liveness signal and made the whole design robust *by construction* rather than dependent
  on the very event a crash suppresses.
- **Brainstorming + 3 scoped AskUserQuestions** — pinned the fork (durable protocol vs
  one-time cleanup), capture depth, and gate assertiveness up front, so the plan had no
  re-litigated decisions.
- **TDD on a pure core with injected effect-fns** — `classify()` takes
  `transcript_mtime_fn`/`pid_alive_fn`/`at_risk_fn`, so the entire truth table is unit-tested
  with zero filesystem/process mocking. Red→green was clean.
- **Subprocess hook smoke tests with an isolated `HOME`** — running each hook as a real
  process against a temp `USERPROFILE` caught the wiring (stdin parse, output shape, gate
  block/override) that pure unit tests can't.
- **Delegating the 10-plan summary to one Explore agent** — kept main context lean while
  producing honest, evidence-backed retros (it checked git history per plan).

## Friction / bugs

- **plan_issue_check blocked the plan write three times**
  - *What happened:* `ExitPlanMode`'s companion hook rejected the plan repeatedly for
    "Retrospective section but doesn't record issue-state changes," even after I added
    `Follows up hb-2ni`.
  - *Root cause:* Rule 2 scans the **Retrospective section body specifically**, and
    `strip_code_spans_and_fences()` removes backticked spans first — so my `` `Closes <id>` ``
    and a `Follows up` line placed in a *different* section both failed the regex.
  - *How caught:* read the hook source (`plan_issue_check.py`) instead of guessing a third time.
  - *Fix:* put a plain-text `Follows up hb-2ni` line *inside* the Retrospective body.
  - *Rule:* the issue-state ref must be plain text **in the Retrospective body** — never
    backticked, never in a sibling section.

- **Site-docs commit re-dirtied itself**
  - *What happened:* committing the 28 `site/content/docs` files left the same 28 files
    modified immediately after.
  - *Root cause:* the path-gated post-commit publish chain (`publish.ps1`) re-stamps
    `date:`/`Trace ID:` to the current day on every publish.
  - *How caught:* re-ran `git status` after the commit instead of assuming it was clean.
  - *Fix:* commit the stamp once more — a same-day re-stamp is idempotent, so the tree settles.
  - *Rule:* after committing anything under the publish path-gate, re-check status; expect
    one idempotent re-stamp commit to reach a fixed point (don't chase it across days).

- **`tsconfig.tsbuildinfo` leaked into the dashboard commit**
  - *What happened:* a TS incremental-build artifact got committed with the 70 dashboard files.
  - *Root cause:* the app's `.gitignore` block didn't exclude `*.tsbuildinfo`.
  - *How caught:* `git show --stat HEAD` after the commit.
  - *Fix:* added the exclusion + `git rm --cached` (commit `8100015`).
  - *Rule:* on the first commit of a TS project, grep the staged set for build artifacts
    (`tsbuildinfo`, `dist/`) before committing.

## Concrete improvements

- **Recovery protocol** — `~/.claude/hooks/{_recovery_lib,session_recovery_*}.py` + `skills/recover/SKILL.md`, registered in `~/.claude/settings.json`. Status: done (activates on next Claude restart).
- **Test harness** — `~/.claude/hooks/test_recovery.py` (24 tests: pure core + subprocess hook smoke). Status: done, green.
- **Memory** — `project_session_recovery.md` records the protocol for future sessions. Status: done.
- **Follow-up** — un-skip/extend with an SDD-ledger-reconciliation step in `/recover` once a real abnormal-exit is triaged in anger. Status: follow-up (not yet needed).
