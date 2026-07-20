# Retrospective: Overnight-hang root cause + Phase 2 remediations

**Plan:** `~/.claude/plans/i-m-trying-to-figure-mutable-reddy.md`
**Commit:** `41c0cd2` (`fix(hooks): scope router matcher to side-effecting tools (hb-0nh)`) + `9738719` (`fix(nightly): add 900s watchdog to kill hung nightly.py`)
**Date:** 2026-07-08 _(catch-up retro authored 2026-07-20)_

## Outcome

Confirmed the root cause of overnight session hangs via read-only measurement, then applied reversible Phase 2 remediations. The initial single-cause hypothesis (Windows Defender per-spawn scan tax) was **falsified** — under 12-way load Defender was only ~2.5x worse than idle. Measurement redirected effort to the actually-confirmed culprits: an 8s per-session CIM sweep in `detect_stale_system_control.py` (>150x degradation under load → fixed with a socket fast-path), a 75.5 MB unbounded `observations.jsonl` re-scanned on every append (→ rotation), and a genuine 03:00 nightly-task collision (→ steward retimed to 03:30). Five of six Phase 2 items landed. **One item genuinely remains** (see below).

## What worked

- **Read-only Phase 1 measurement before remediation** — the spawn-latency baseline + hook-cost accounting cleanly falsified the Defender hypothesis and pointed at the real causes. The decision gate ("if Defender isn't confirmed dominant, stop and re-investigate") did its job and prevented blindly pursuing Defender exclusions as the primary fix.
- **Reversible remediations only** — socket fast-path, log rotation, task retime, 900s nightly watchdog, and a hook diet, all individually revertible.

## Friction / bugs

- **Bundled elevated-evidence step blocked the whole line item**
  - *What happened:* Phase 1's "read exclusion list" (admin) and "apply Defender exclusions" (admin) were collapsed into a single Phase 2 checkbox, so a blocked admin read left the whole item un-actionable.
  - *Root cause:* Two separately-sequenceable steps (measure-under-elevation vs. apply-exclusion) were tracked as one checkbox.
  - *How caught:* This retro's evidence pass — `Get-MpPreference` still returns "must be an administrator," `hardware-profile.md` records no exclusions, and no `Add-MpPreference` script exists anywhere.
  - *Rule:* Track an admin-gated *measurement* separately from the *action* it gates — collapsing them makes "blocked on evidence" indistinguishable from "not done."

## Concrete improvements

- Socket fast-path in `detect_stale_system_control.py` — done (hb-0nh).
- `observations.jsonl` rotation / cap — done.
- Steward retimed 03:00 → 03:30; `run_nightly.ps1` 900s watchdog — done.
- Hook diet (router scoped to side-effecting tools) — done.
- **REMAINS / needs user action:** Defender path + process exclusions (elevated). Deferred — the confirmed causes are already fixed, so the exclusion value is now uncertain. Requires an admin PowerShell session Claude cannot self-serve. Decision pending: apply anyway (defense-in-depth for large workflows, orbits hb-x91) or formally drop. Also flagged: `Roleplaying/.claude/settings.local.json` still runs superseded per-edit cargo/tsc/eslint hooks alongside the newer dirty-flag+Stop design — a separate follow-up thread, out of this plan's scope.
