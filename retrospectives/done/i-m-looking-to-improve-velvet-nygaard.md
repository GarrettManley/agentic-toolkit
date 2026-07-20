# Retrospective: delivery `deliver` — explicit writing-plans invocation + seam contract test

**Plan:** `~/.claude/plans/i-m-looking-to-improve-velvet-nygaard.md`
**Commit:** `be6c75f` (`fix(delivery): invoke writing-plans explicitly and suppress its execution hand-off (#26)`)
**Date:** 2026-07-01 _(catch-up retro authored 2026-07-20)_

## Outcome

Fixed the delivery plugin's `deliver` skill so Phase A step 3 explicitly invokes `superpowers:writing-plans` and suppresses its own execution hand-off, mirroring the suppression pattern already used at the Phase 0 and Phase B seams. Added a parametrized contract test (`TestComposedHandoffsAreSuppressed`) enforcing all three seams so a future edit can't silently drop one. Landed via squash-merge PR #26 (`claude-marketplace`); `pytest plugins/delivery/tests/test_deliver_contract.py` → 23 passed today, confirming the fix is intact through the plugin's subsequent progression to v0.3.1. All 16 plan tasks landed but were never ticked — this was a bookkeeping gap, not incomplete work.

## What worked

- **Reusing the existing Phase 0/Phase B suppression wording** on Phase A fixed the reported re-invoke friction in one coherent commit — no new pattern invented.
- **Em-dash-anchored `section()` heading match in the contract test** proved robust across all three seams; no fragility observed on re-run.

## Friction / bugs

- **`ci/release.py --apply` proposed a spurious `0.3.0` bump plus unrelated plugin bumps**
  - *What happened:* The prescribed version-bump tooling misbehaved.
  - *Root cause:* The delivery plugin had no `delivery-v0.2.0` git tag, so release.py's tag-anchored diff range fell back to the plugin's full history and over-bumped — and swept in the discipline/review plugins.
  - *How caught:* Reviewing the release.py dry-run output before applying.
  - *Fix:* Hand-edited the version in `plugin.json`/`marketplace.json`/`SKILL.md` frontmatter (the repo's documented hand-editable source of truth); flagged the missing tag as pre-existing/out-of-scope.
  - *Rule (generalizable):* A missing `<plugin>-v<prev>` tag makes `release.py` fall back to full-history and over-bump — re-point/backfill the tag before trusting a release.py bump. _(Matches the learned instinct about stale release tags.)_

## Concrete improvements

- Explicit `writing-plans` invocation + execution-handoff suppression at Phase A — `plugins/delivery/skills/deliver/SKILL.md`, done.
- 3-seam contract test — `plugins/delivery/tests/test_deliver_contract.py`, done.
- **Follow-up:** backfill the `delivery-v0.2.0` (and sibling) release tags so `release.py` stops falling back to full history. Pending — surfaces every release cycle.
