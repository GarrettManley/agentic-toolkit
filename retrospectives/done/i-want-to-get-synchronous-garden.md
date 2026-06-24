# Retrospective: Recovery Plan — clear the crash-recovery gate (session `7d3e6e60`)

**Plan:** `~/.claude/plans/i-want-to-get-synchronous-garden.md`
**Commit:** n/a — no code change; the only state-changing step was `_recovery_lib.py resolve`
**Date:** 2026-06-24

## Outcome

Exercised the hb-bam crash-recovery protocol on an abnormally-exited prior incarnation of
session `7d3e6e60` (Workspace / master). Read-only triage confirmed a **no-op recovery** — the
dead session began and ended in a fully-committed, fully-merged state (sentinel
`dirty_at_start: []`, HEAD == sentinel `head_sha` `1f91cab`, SDD ledger matched reality,
handoff already current). Cleared the gate by resolving the sentinel on 2026-06-23; nothing
was committed, stashed, or lost. Optional stale-worktree housekeeping was left opt-in.

## What worked

- **Sentinel JSON over the pending-summary string** — the `recovery-pending.json` summary read
  "…Temp (branch main)" (generic/stale), but the sentinel JSON ("Workspace / master /
  `1f91cab`") was authoritative. Trusting the structured sentinel, not the human-readable
  summary, prevented a wrong-cwd investigation.
- **Evidence table before action** — a 7-row read-only verification table (dirty_at_start,
  porcelain, HEAD vs head_sha, SDD ledger, handoff, retros, stash list) made the no-op
  conclusion auditable before touching any state.
- **Worktree triage that distinguished prunable from load-bearing** — `agent-ac0653…`
  (unmerged Stage 4c sandbox work, matches open hb-s2c/hb-ctr) was correctly flagged **keep**
  rather than swept up with the two already-merged/superseded worktrees.

## Friction / bugs

- **Stale/misleading recovery-pending summary string**
  - *What happened:* the gate's summary labeled the crash as "Temp (branch main)" when the dead
    session was actually Workspace / master.
  - *Root cause:* the pending-summary is a generic label, not regenerated from the authoritative
    sentinel JSON at write time.
  - *How caught:* cross-checking the summary against the sentinel `cwd`/`branch`/`head_sha`.
  - *Fix:* none needed for this recovery (used the sentinel); noted as a protocol observation.
  - *Rule:* during `/recover`, always reconcile the pending summary against the sentinel JSON —
    the sentinel wins. (Recurred in the 2026-06-24 recovery, where the same "Temp / main"
    summary again masked the real Workspace/master session — confirms the rule.)

## Concrete improvements

- **No new beads spawned** — the crash lost nothing; pre-existing follow-up stays under hb-yz5
  (Stage 5/6 deferred items). Status: done.
- **Worktree housekeeping** — prune the two safe worktrees (`agent-a1d164d6…`, `agent-a58986…`),
  keep `agent-ac0653…` for hb-s2c. Status: opt-in, not executed.
- **Protocol observation (recovery-pending summary drift)** — candidate hardening for hb-bam:
  regenerate the pending summary from the sentinel rather than a generic label. Status:
  follow-up, not bead-worthy yet (observed twice).
