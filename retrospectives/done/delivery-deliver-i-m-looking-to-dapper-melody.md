# Retrospective: Improve the `delivery` plugin (`deliver` skill) — v0.1.0 → v0.2.0

**Plan:** `~/.claude/plans/delivery-deliver-i-m-looking-to-dapper-melody.md`
**Commit:** `266fbf1` (`docs(delivery): add 0.2.0 CHANGELOG entry`) on `feat/delivery-v0.2.0`, PR
[#21](https://github.com/GarrettManley/claude-marketplace/pull/21)
**Date:** 2026-06-30

## Outcome

Shipped `delivery@garrettmanley` v0.2.0: a positive-evidence completion gate (wiring
`verification-before-completion`'s Iron Law into the artifact `plan_completion_check.py` actually
inspects, not just unenforced prose), hardened gate wording at all three review gates, a
worktree-freshness guard, two-tier code review at full model capability, Hybrid landing that delegates
to `finishing-a-development-branch` instead of reinventing it, a dependency-manifest fix, a verified
dogfood/publish-loop doc, Phase B resumability riding on SDD's native ledger, an optional Design Phase
0 with objective skip-conditions, and an optional `constitution` governance key. The work itself was
delivered *through* `/deliver` — the first time the skill has actually run end-to-end rather than been
performed by hand. Tracker: hb-w61.5.

## What worked

- **Adversarial plan review before any code** caught a technically-broken design (the original WS3's
  `/recover` hook pointed at infrastructure outside the plugin, reconciling the wrong ledger) before a
  line was written — rescoped to reuse SDD's existing ledger instead.
- **Per-task review with a fresh subagent** caught real defects on tasks that looked complete: a dead
  branch in Landing-policy logic (Task 1), and residual subjectivity in a "make this objective" trigger
  that took *two* fix rounds to actually close (Task 4) — the first fix attempt was still too broad.
- **Whole-branch review at full session model, no down-routing** caught two CRITICAL logic conflicts
  five individually-clean per-task reviews missed entirely: Phase 0 dispatching `brainstorming` before
  `pre-plan-brief` (violating that skill's own documented contract), and Phase 0 lacking a
  stop-before-hand-off instruction for `brainstorming`→`writing-plans` — the same bug class already
  fixed elsewhere in the same branch for SDD→`finishing-a-development-branch`. This empirically confirms
  the plan's own two-tier-review rationale, not just its theory.
- **The re-review loop caught the fixer's own mistake**: a fix for the completion gate claimed a regex
  mechanically enforced a check it didn't (verified false by direct regex testing against the actual
  hook). This is the exact "confident fabrication" anti-pattern flagged during the plan's own
  deep-research phase, now observed firsthand inside the work it produced — and caught by the next
  review round rather than shipping.
- **Empirical-over-assumed**, applied to the controller's own actions: rather than guessing at the
  dev-test mechanism for WS2, the controller live-tested `claude plugin marketplace` and
  `--plugin-dir` commands directly, surfacing a genuine and non-obvious gotcha (declared `dependencies`
  break standalone `--plugin-dir` loading) that no amount of reading docs would have found.

## Friction / bugs

- **Marketplace registry destructive round-trip**
  - *What happened:* `claude plugin marketplace add <local-path> --scope local` followed by
    `marketplace remove --scope local` deleted the live user-scope `garrettmanley` GitHub registration
    from `known_marketplaces.json` entirely, instead of safely undoing the local shadow.
  - *Root cause:* marketplace names are derived from `marketplace.json`'s own `name` field, not chosen
    by the operator — a local-path add of this repo always collides with the live entry's name, and
    `remove` on that collision deletes rather than restores.
  - *How caught:* an immediate post-condition check (`marketplace list`) after the planned cleanup
    step, before moving on to anything else.
  - *Fix:* `claude plugin marketplace add GarrettManley/claude-marketplace` restored it; verified via
    `marketplace list` showing the GitHub source again. No plugin content or cache was lost.
  - *Rule:* never recommend `marketplace add`/`remove --scope local` round-tripping as a dev-test
    mechanism — documented as a hard warning in the shipped doc itself. Use `claude --plugin-dir`
    instead (verified safe, zero registry mutation).
- **Dev-clone location outside any documented project root**
  - *What happened:* the dev clone lived at `~/source/repos/claude-marketplace/`, a path sibling to
    `Workspace/` rather than nested in it — caused real confusion mid-session (an Explore agent
    searched `Workspace/source/repos/` and correctly found nothing, since the path didn't exist there).
  - *Fix:* relocated to `~/Workspace/claude-marketplace/` (surfaced by the user mid-session, not
    originally planned); updated `AGENTS.md`'s project-root listing and added a memory entry.
  - *Rule:* keep dev-clone repos nested under a documented project root, not a sibling directory.

## Concrete improvements

- **`delivery@garrettmanley` v0.2.0** — shipped on `feat/delivery-v0.2.0`, PR #21 open for review/merge.
- **`~/Workspace/claude-marketplace/`** — dev clone relocated here; `AGENTS.md` updated; memory entry
  `reference_marketplace_location.md` added.
- **hb-w61.6** (filed, not executed) — design a `/workflows`-native execution variant of `deliver`'s
  Phase B, surfaced mid-session: Workflow's `resumeFromRunId` agent-call caching is a cleaner
  resumability fix than this plan's own WS3 rescope, which only covers Phase B via SDD's ledger.
- **hb-3i0** (filed, not executed) — a session-start command codifying the "next highest-value body of
  work" pattern visible across multiple retro titles in this history.
- **Deferred, not done:** the full interactive 12-step `/deliver` lifecycle E2E, and a crash/resume
  test against the SDD ledger — both genuinely require a separate live multi-turn session, explicitly
  flagged as open in the plan's Verification section rather than claimed complete. Recommend a
  follow-up `/deliver` dry-run before relying on v0.2.0 for real work.
- **WS5's `constitution` key has no consumer yet** — kept in scope over unanimous adversarial-review
  pushback per explicit user direction; revisit at a future retro if no repo has bound it by then.
