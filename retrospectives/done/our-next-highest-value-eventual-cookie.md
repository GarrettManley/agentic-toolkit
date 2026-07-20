# Retrospective: Aether #289 — Arc-3 combat & creation correctness regressions

**Plan:** `~/.claude/plans/our-next-highest-value-eventual-cookie.md`
**Commit:** `6e4e878` (`fix(combat): Arc-3 combat & creation correctness regressions (#289)`); Step 0 `9738719` (nightly watchdog); retro `95844a4`
**Date:** 2026-07-08 _(catch-up retro authored 2026-07-20)_

## Outcome

Landed the #289 fix wave in `Roleplaying/` — 3 HIGH + 2 MED regressions plus 3 LOW cleanups found by the 051 delta audit: pcSlug/creatureSlug slug drift, a stranded ActorAgent NPC at the initiative head, `parse_damage_dice` rejecting flat damage, `encounter.end()` throwing past the teardown catch, and a lobby name-gate looser than the wizard gate. A Step 0 prerequisite — committing the inherited sec-research nightly watchdog and clearing the session-recovery gate — was cleared first. Full gate green (192 Rust tests, 1605+28 TS tests) before landing. A full retro already lives in-repo at `Roleplaying/retrospectives/done/2026-07-08-289-arc3-regressions.md`; this closes the pending marker.

## What worked

- **Read the write-side before patching the read-side** — reading `sanitizeName` before touching the pcSlug bug turned a regex patch into a DRY delete-the-duplicate fix.
- **Verify the exact match condition before writing the fix** — tracing `actor.ts:78`'s `STAGE_DIRECTIONS` match got the cue-fix payload shape right first try.
- **Check all call sites before choosing a fix shape** — inspecting every `runMonsterTurns` caller avoided a double-fire regression disguised as a fix.

## Friction / bugs

- **Two unrelated prerequisites blocked the start**
  - *What happened:* A prior session's abnormal-exit recovery gate and a stale (but accurate) handoff doc for an already-merged #263 both had to clear before #289 could begin.
  - *Root cause:* Inherited cross-session state — the recovery gate and a not-yet-cleared handoff.
  - *How caught:* Session-start recovery report + the plan's explicit Step 0.
  - *Rule:* Treat inherited recovery-gate + stale-handoff clearing as an explicit Step 0, not an assumption — sequence it before the real work.

## Concrete improvements

- #289 fixes (combatant-resolve, dm.ts, gateway/server.ts, creature_attack.rs + tests) — done.
- ts-module-graph regenerated post-fix (`6da0255`) — done.
- **Learning-mode split noted:** two genuine design decisions (flat-damage tuple representation; `encounter.end()` teardown-failure strategy — swallow+telemetry chosen) were scaffolded and handed off rather than auto-applied. Deliberate; worked well as a pattern.
