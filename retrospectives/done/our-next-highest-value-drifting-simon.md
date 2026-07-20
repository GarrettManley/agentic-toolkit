# Retrospective: Hook-error observability (hb-rap) + systemic UTF-8 defense (hb-zxg)

**Plan:** `~/.claude/plans/our-next-highest-value-drifting-simon.md`
**Commit:** `ff7fd4c` (PR #57 merge: `fix: hook-error observability + systemic UTF-8 defense in run_with_flags (#57)`) → release `7641558` (`chore(release): discipline@1.2.1, learning@1.6.1, stewardship@1.4.2`)
**Date:** 2026-07-10 _(catch-up retro authored 2026-07-20)_

## Outcome

Hardened hook reliability across the marketplace as one coordinated 3-plugin change: (1) **hb-rap** routes wrapper-swallowed hook errors from `run_with_flags.py` to a shared JSONL sink surfaced in the stewardship morning briefing, replacing silent stderr-only swallowing; (2) **hb-zxg** reconfigures `run_with_flags.py`'s stdio to UTF-8 so a hook's non-ASCII output can't crash a strict cp1252 console, generalizing the narrow per-entry-point fix from ADR-0014/PR #52. Landed via PR #57 with a coordinated release (discipline canonical + learning/stewardship re-synced); tags `discipline-v1.2.1` / `learning-v1.6.1` / `stewardship-v1.4.2` confirmed on `main`. A companion topic-retro exists at `retrospectives/done/2026-07-10-hb-zxg-utf8-defense.md` (substance current; its "PR pending" landing status predates the actual merge). The plan's final release-preview checkbox went un-ticked but the work went further than the dry-run — full apply → merge → tag.

## What worked

- **Full adversarial plan review before building** — caught that hb-rap was already implemented and reviewed on an unmerged branch (`fix/hb-rap-hook-error-observability`) before duplicate work started, forcing a clean mid-flight pivot to "adopt hb-rap + stack hb-zxg" instead of building from scratch.
- **Reproduce-before-trust** — proved the plan's regression test targeted the wrong stream (stderr, which uses `backslashreplace` and never raises); rewritten to target stdout, the actual strict-cp1252 crash site.
- **Whole-branch code review** — caught a live CRITICAL: `reconfigure(encoding="utf-8")` silently resets the error handler to strict, stripping stderr's `backslashreplace` safety net.

## Friction / bugs

- **`reconfigure(encoding=...)` silently resets `errors` to strict**
  - *Root cause:* Python's `TextIOWrapper.reconfigure` defaults `errors` back to strict unless explicitly preserved.
  - *How caught:* Full-capability whole-branch review.
  - *Fix:* Pass `errors=stream.errors` to preserve the existing handler.
  - *Rule:* When calling `reconfigure(encoding=...)`, always re-pass `errors=` or you silently lose the stream's error handler.
- **Test pollution of the real `%LOCALAPPDATA%` hook-error sink**
  - *What happened:* Early manual test runs wrote to the real `hooks-errors.jsonl`, which then crashed the stewardship briefing tests reading that same real file.
  - *Root cause:* Isolation-fixture gap — tests touched a real per-machine path (a scar already named in the hb-rap retro).
  - *Fix:* Isolated the sink path in the fixture; also hardened `render_briefing`'s strict-UTF-8 write against a surrogate in a hook-error message.
  - *Rule:* Any test that can write a plugin's real per-machine data file must redirect that path in a fixture — re-triggered scar.
- **Plan-mode Explore agents missed the unmerged hb-rap branch** — they checked beads/current-state but not `git branch --list`. *Rule:* when scoping "next work," include `git branch --list -a` so unlanded prior work is visible.

## Concrete improvements

- Shared hook-error JSONL sink + briefing surfacing (hb-rap) — done.
- UTF-8 stdio + preserved error handler in `run_with_flags.py` (hb-zxg) — done.
- Downstream `render_briefing` surrogate-safe write — done.
- Coordinated 3-plugin release + post-merge tags (ADR-0012 tags-born-on-main) — done.
