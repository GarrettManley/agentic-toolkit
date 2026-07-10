# Retrospective: hb-rap — Hook-error observability

**Plan:** `claude-marketplace/docs/superpowers/plans/2026-07-09-hb-rap-hook-error-observability-plan.md`
**Commits:** branch `fix/hb-rap-hook-error-observability` (10 commits; final code `3160ae9`); PR pending user authorization.
**Date:** 2026-07-09

## Outcome

Delivered hb-rap through the full `/deliver` lifecycle. `run_with_flags` (vendored 3×) now persists swallowed hook import/runtime errors to a bounded `<learning_data_root>/hooks-errors.jsonl`, and the stewardship morning briefing surfaces a count + recent samples via a new `## Hook Errors` section — so a `surface.py`-style silent hook crash becomes visible within a nightly cycle instead of going unnoticed for weeks. The delivery began as a much larger design and was cut to essentials by adversarial review + a user approach-decision.

## What worked

- **The FULL plan review earned its cost, twice over.** It caught two *execution* CRITICALs (tests would pollute the developer's real log; `release.py` bumps by commit *scope* not changed files, so the vendored sync would never bump `learning` — the plugin whose copy wraps `surface.py`), plus a premise challenge (a ~2-line `return 1` alternative). Without it, this ships broken *and* over-built.
- **Surfacing the premise fork to the user instead of deciding it.** "Loud/immediate (exit 1) vs quiet/persistent (log+briefing)" is a UX policy for the user's hook system — I verified the exit-1 alternative's viability against the Claude Code docs (`claude-code-guide`) so the choice was informed, then let the user pick (they chose log+briefing).
- **The whole-branch code review caught the *ironic* bug.** The error-logger's own `except Exception: pass` was itself a silent failure — in a feature built to end silent failures. Also a `UnicodeDecodeError` crash path and a resolver-agreement test that only tested the trivial branch. All fixed in a per-plugin fix-wave.
- **The intricate vendored-3× + per-plugin-commit + scoped-isolation-fixture dance executed cleanly inline** — safer than dispatching into the nested clone.

## Friction / bugs

- **Over-built the initial plan for a P3**
  - *What happened:* the first plan added log + briefing + a new `CLAUDE_MARKETPLACE_DATA_ROOT` env + a second resolver + a `derive_actions` rule.
  - *Root cause:* designed maximally without first pricing the bead's "implement ONE of three" scoping or the ~2-line `return 1` alternative.
  - *How caught:* scope-cut dimension + scope-cutter + skeptic converged.
  - *Rule:* for an observability / "implement one" bead, start from the *minimal* option and justify each addition; price the trivial alternative before building a subsystem.
- **Test pollution of the real signal (CRITICAL)**
  - *Root cause:* added a filesystem side-effect to a vendored hot-path function that *existing* tests already exercise, without auditing those tests for isolation.
  - *Rule:* when adding a filesystem side-effect to a shared/vendored function, audit EVERY test that reaches it (all vendored copies' suites), not just the new tests. Scope isolation fixtures carefully — learning's suite had a `test_home_fallback_when_no_env` that needed the env *unset*, forcing a class-scoped (not module-wide) fixture.
- **Release-scope-not-path (CRITICAL)**
  - *Root cause:* `release.py` derives per-plugin bumps from commit *scope*; a single `fix(discipline)` commit carrying vendored copies never bumps the consumers.
  - *Rule:* a vendored-file change must ship as per-plugin-scoped commits (`fix(discipline)` + `fix(learning)` + `fix(stewardship)`), each staging its own copy.
- **Multi-dir pytest collection collision**
  - *Root cause:* `test_run_with_flags.py` exists in both discipline and stewardship; a single `pytest dirA dirB` invocation collides on the basename. My own Verification command had this bug.
  - *Rule:* always per-plugin-dir pytest in this repo (as CI does).

## Concrete improvements

- **Land pending** — branch `fix/hb-rap-hook-error-observability` (10 commits) awaits authorization to push + open a PR (`land-policy: pr`). **hb-rap stays open until merge.** `release.py --dry-run` confirms all three plugins bump.
- The "surface a genuine fork to the user with a verified recommendation" move (here, loud-vs-quiet error visibility) is reusable whenever a review challenges a plan's premise on a decision that's really the user's.
