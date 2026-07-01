# Retrospective: Context-Compaction Skill Suite (discipline plugin)

**Plan:** `~/.claude/plans/role-principal-ai-architect-mossy-snowflake.md`
**Commit:** `06934e4` (`fix(discipline): validate discovered plan paths, fail-soft marker stat, clarify note-key docs`) — branch `feat/compact-plan`, PR [#45](https://github.com/GarrettManley/claude-marketplace/pull/45), closes [#44](https://github.com/GarrettManley/claude-marketplace/issues/44)
**Date:** 2026-07-01

## Outcome

Shipped a compaction-survival suite for `discipline` with zero wiring changes: `plan_state.py` (live workflow-state discovery + a TTL'd intent-note sidecar), workflow rendering in the existing SessionStart resume hook, a `compact_plan_state.py` CLI, and the `/discipline:compact-plan` skill. Delivered via the full deliver lifecycle: FULL 9-agent plan review (which **redesigned the architecture pre-code**), 5 SDD tasks with per-task reviews, whole-branch review (which caught a production-killing CRITICAL), adversarial code review, PR landing. Combined coverage 98%; all gates green. Landed as PR #45 — merge pending the 5 required checks. **Activation caveat:** `discipline@garrettmanley` is currently installed but *disabled*; the suite is inert until re-enabled.

## What worked

- **Adversarial plan review as architecture input, not just gate** — the plan-skeptic's live-compute finding ("everything except the note is recomputable from disk; persist only the note") deleted an entire task, the schema-v2 manifest, and the carry-forward machinery before any code existed. Second consecutive delivery where the FULL posture reversed a wrong build.
- **Two-tier review at different scopes** — per-task reviewers (sonnet) verified transcription fidelity cheaply; the whole-branch review at session tier caught the note-key divergence no task-scoped diff could see. The split earned its cost precisely at the seam between tasks.
- **Dossier fact-checking before design** — the user-supplied R&D dossier was mostly accurate on repo facts but wrong on the core mechanism (hooks cannot inject compaction prompts; `/compact` is user-typed only). Verifying every claimed file and extension point (Explore agents + claude-code-guide + the in-repo `pre_compact_snapshot.py` docstring) prevented building the whole feature on a false premise.
- **Step-0 gating spike caught a dead deployment target** — before Task 1, checking the live environment revealed `discipline` is installed but disabled ("installed ≠ enabled", again). Surfaced to the user instead of silently editing plugin config.
- **Worktree isolation survived a mid-delivery recovery interlude** — `/recover` (parallel-session cleanup, home-repo commit, sentinel resolution) ran between the fixer dispatch and re-verify with zero interference to the branch.
- **Asymmetric-env smoke as the regression proof** — re-running verification with `CLAUDE_PROJECT_DIR` unset on the CLI side and set on the hook side proved the Critical's fix live, and dogfooded the feature against this very delivery's own SDD ledger.

## Friction / bugs

- **Note sidecar keyed differently in hook vs CLI contexts (CRITICAL, caught at whole-branch review)**
  - *What happened:* `get_note_path()` used `snapshot.get_project_key()`, which branches on `CLAUDE_PROJECT_DIR` — set for hook processes, absent from the Bash-tool env. The CLI wrote the note under the git-remote hash; the hook read under the path hash. The flagship persisted artifact silently never rendered.
  - *Root cause:* every test fixture AND the plan's smoke procedure pre-set `CLAUDE_PROJECT_DIR` on both sides — the exact env var whose absence defines production.
  - *How caught:* whole-branch reviewer (session tier) computed both keys live and showed the mismatch (`8c279ed40dde` vs `385465cb6eb3`).
  - *Fix:* root-anchored key (`_short_hash(get_project_root().resolve())`) converging in both contexts + a cross-context round-trip test that deliberately unsets the env var on the write side (`1ab9c16`).
  - *Rule:* **for any env-branched derivation (keys, paths, config), at least one test must run in the degraded env configuration** — symmetric fixtures mask exactly the divergence that ships.
- **Plan-inherited defects dominated the findings**
  - *What happened:* nearly all review findings (note key, loose `.md` regex, coupled try/except, missing merge-branch test) were transcribed faithfully from the plan's own code blocks; implementers were blameless.
  - *Root cause:* writing-plans' complete-code-in-plan style moves defect risk from implementation to planning; per-task "exact transcription" reviews then structurally cannot catch them.
  - *How caught:* only the wider-scope reviews (whole-branch + silent-failure-hunter).
  - *Rule:* when the plan carries complete code, weight review budget toward the whole-branch tier — per-task review of transcription tasks is a fidelity check, not a correctness check.
- **Glob false-negatives into the marketplace (recurring, third occurrence)**
  - *What happened:* `Glob` with `path:` into `claude-marketplace` returned "No files found" for files that exist (`plugins/delivery/skills/deliver/SKILL.md`, `tests/test_s*.py`).
  - *How caught:* prior-retro brief warned about it; verified with `ls` before trusting.
  - *Rule:* in this repo, verify any negative Glob result with `ls`/Bash before acting on it.
- **SDD helper scripts write to the cwd's repo, not the worktree**
  - *What happened:* the first `task-brief` run wrote into the main checkout's `.superpowers/sdd/` (next to the stale audit ledger) because the shell cwd hadn't entered the worktree yet.
  - *Fix:* moved the file; ran all subsequent script invocations from the worktree.
  - *Rule:* `task-brief`/`review-package` resolve against `git rev-parse --show-toplevel` of the cwd — cd into the worktree before the first dispatch.

## Concrete improvements

- **Deferred (tracked on #44):** note keying when the CLI runs from a checkout other than the session's project dir — mitigated with a SKILL.md "run from the project root" contract line; a mechanical fix needs live verification that `${CLAUDE_PROJECT_DIR}` expands in skill bodies.
- **Activation (user action):** re-enable `discipline@garrettmanley` (plus any other intentionally-enabled plugins from the pruned set — only delivery/docs/retrospective are currently enabled) or the suite never fires; then merge PR #45, run `ci/release.py` (feat → 1.2.0), reinstall via `/plugin`.
- **Declined with reason:** empty `--note ""` handling (skill-driven input; repo preference against phantom-input validation).
- **Residual minors** recorded in the worktree ledger (dense ternary, double `_sdd_ledger` read, ascii-test weakness, `+N more` overflow untested, future-dated note TTL nit) — none merge-blocking.
