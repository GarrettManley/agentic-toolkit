# Retrospective: Pending-retrospective cleanup (4 markers)

**Plan:** `~/.claude/plans/playful-hugging-lobster.md`
**Commit:** the `docs(retro)` commit that adds this file (Workspace `master`)
**Date:** 2026-06-28

## Outcome

Cleared a recurring SessionStart nag about four "outstanding plan retrospectives" by triaging
each against its tracker instead of mass-writing retros. Only one plan (`hb-2ni`, the aether
per-edit hook debounce) was actually complete → it got a real retrospective. The other three
markers were premature: `hb-322` ran its first supervised run but its DoD is unmet (deferred),
`hb-0vq` has only Phase 0 shipped (marker cleared), and Aether QP#2 (`#220`) was never started
(marker cleared). Net: 1 retro written, 3 markers removed, 1 left as an accurate reminder.

## What worked

- **Tracker-first triage before writing anything.** `bd show hb-2ni hb-322 hb-0vq` + `gh issue
  view 220` + `gh pr view 231` + git log established the real state in a few read-only calls and
  immediately exposed that 3 of 4 markers were premature — flipping the task from "write 4 retros"
  to "write 1, decide on 3."
- **Refusing to fabricate completion.** The honest move was *not* writing "done" retros for
  in-flight / unstarted work; the `retrospectives/done/` record stays trustworthy.
- **AskUserQuestion for the genuine judgment calls.** Defer-vs-clear on the incomplete plans is
  the user's workflow-hygiene decision, not a default — one tight 2-question prompt resolved it.

## Friction / bugs

- **The retro-marker fires at plan-finalize, not at plan-completion.**
  - *What happened:* All four markers existed despite three plans being incomplete; the nag read
    as "4 retros owed" when only 1 was.
  - *Root cause:* `exit-plan-mode-marker.sh` drops the pending marker at ExitPlanMode (plan
    *created*), so any plan that's finalized but then stalls, spans sessions, or is abandoned
    becomes a false "retro owed" signal.
  - *How caught:* Cross-checking each marker's slug against its tracker state.
  - *Rule:* Treat the SessionStart "outstanding retrospectives" list as *"verify completion,"*
    not *"write retros now"* — confirm the underlying work actually shipped before retro-ing, and
    clear markers for premature/abandoned plans.

## Concrete improvements

- **1 retrospective written** — `retrospectives/done/writing-plans-let-s-write-a-iterative-minsky.md`. Status: done.
- **3 markers cleared** — iterative-minsky (via retro), golden-cloud + jiggly-mccarthy (premature). Status: done.
- **glimmering-salamander (hb-322) marker retained** — retro owed once it reaches a defensible
  finding-or-null outcome (blocked on hb-0vq). Status: pending, correctly.
- **Observation (no action taken):** the marker mechanism could create the pending marker at
  work-completion rather than plan-finalize to avoid premature nags — a plugin-design change for
  the `retrospective@garrettmanley` plugin, noted here rather than actioned.
