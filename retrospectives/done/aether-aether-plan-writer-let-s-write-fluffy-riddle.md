# Retrospective: 128 — Correct the false "infinite memory" claim + reconcile the stale issue tracker

**Plan:** `~/.claude/plans/aether-aether-plan-writer-let-s-write-fluffy-riddle.md`
**Commit:** `05dd719` (`docs: correct false "infinite memory" claim + stale contextTokens comment (#128)`)
**Date:** 2026-06-29

## Outcome

Full retrospective lives at `Roleplaying/retrospectives/done/issue-tracker-reconciliation-128.md` (this plan executed against the aether-engine repo nested under `Roleplaying/`). This is a thin pointer clearing the Workspace-root pending marker; see the linked file for the complete write-up.

## What worked

- Verify-before-close discipline: every "done-but-open" issue (#201/#202/#236) was checked against commits/code before closing, catching drifted citations from the original survey pass.

## Friction / bugs

- **Stale-doc trap recurrence** — exploration agents twice reported already-shipped work (spec-047, TTS cluster) as open value gaps before this plan corrected the tracker itself.

## Concrete improvements

- Tracker (#128, #235) now carries dated, accurate status instead of stale/overstated notes.
- `retrospectives/pending/` was flagged as holding ~11 stale markers worth a separate cleanup pass — partially addressed by this loop iteration.
