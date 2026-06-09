# Retrospective: Reconcile & close the marketplace epic (hb-28u)

**Plan:** `~/.claude/plans/create-a-plan-for-cryptic-sloth.md`
**Commit:** none in this workspace — the work was beads-ledger reconciliation
(`~/.claude/harness-backlog`) plus a marketplace-repo push; no Workspace files changed.
**Date:** 2026-06-09 (executed 2026-06-04; retro backfilled)

## Outcome

Restored the harness ledger's authority over the marketplace epic. `hb-28u.1/.2/.3`
closed with evidence-bearing reasons (repo private + pushed, all 12 plugins built and
enabled, context hoisted + auto-injected); `hb-28u.4` retitled and re-scoped to
project-migration-only (plugin-build half verified complete); epic note added — 16% → 66%
(4/6). `bd ready` stopped presenting already-shipped Phase 1 work as actionable, and
`hb-rfz` surfaced once `.1`'s dependency cleared.

## What worked

- **Ground-truth verification before build work** — the original ask was "build
  hb-28u.1"; checking the filesystem/repo first showed all three deliverables already
  shipped, converting a build task into a cheap reconciliation pass.
- **Evidence-bearing close reasons** — each `bd close` cites the concrete proof (repo
  visibility, component counts, enabled-plugins entries), so the ledger is auditable
  rather than just updated.
- **Explicit out-of-scope list** — kept the pass from sprawling into plugin refactors or
  cross-machine migration that couldn't be verified from this machine.

## Friction / bugs

- **Stale tracking ref masqueraded as unpushed work**
  - *What happened:* plan assumed "5 unpushed commits" needed pushing; `git push`
    returned *Everything up-to-date*.
  - *Root cause:* local `origin/main` tracking ref was stale — never fetched after a
    push from another context.
  - *How caught:* the push itself (idempotent, harmless).
  - *Fix:* none needed; evidence row corrected in the plan retro.
  - *Rule:* `git fetch` before trusting `ahead/behind` counts in any reconciliation
    audit (same gotcha class as the marketplace repo's `git fetch --tags` rule).

## Concrete improvements

- **Close-the-bead-when-work-ships habit** — root cause of the 16%-vs-reality drift was
  marketplace commits landing with no ledger write-back. Status: addressed structurally
  on 2026-06-09 by the quality-pass epic (`hb-9hv`), whose tasks close their beads in the
  same session the work lands.
- **Tracker-cites-the-status convention held up** — no auto-memory restated epic status,
  so reconciliation touched only the ledger. Status: done (nothing to change).
