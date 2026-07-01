# Retrospective: First Real Supervised Run — sec-research × huntr.com (hb-322)

**Plan:** `~/.claude/plans/writing-plans-let-s-write-a-glimmering-salamander.md`
**Commit:** `4a33016` (`feat(sec-research): supervised pipeline driver + run journal; fixes from first live run (hb-322)`)
**Date:** 2026-06-30

## Outcome

This plan designed the `--supervised` driver, run-journal artifact, and six-checkpoint
walkthrough for hb-322 (first real supervised pipeline run against huntr.com). Execution spanned
a follow-on planning pass authored separately as `~/.claude/plans/the-next-highest-value-pure-kettle.md`
(added the `claude-cli` LLM provider needed to actually drive the run) — that plan's retrospective
at `retrospectives/done/the-next-highest-value-pure-kettle.md` is the canonical, complete write-up
of the executed outcome: hb-322 closed on a ledger-verified defensible null against
`isaacs/minimatch`, two follow-up beads filed (hb-5i3, hb-a2w). This file is a thin pointer
clearing this plan-slug's pending marker; see the linked retrospective for the full account.

## What worked

- Locking scope/provider/driver decisions up front (this plan's "Locked decisions" table) gave
  the follow-on execution plan a stable foundation instead of re-litigating LLM-provider choice
  mid-run.

## Concrete improvements

- **Naming split observed:** when a plan's execution is picked up by a later, separately-authored
  plan file, the retrospective ends up filed under the *later* plan's slug, leaving the
  originating plan's pending marker stale indefinitely. Worth a `retrospective:plan-retrospective`
  note: check for a superseding plan by grepping the same tracker id (`hb-322`) across
  `~/.claude/plans/` before assuming a stale marker means lost work.
