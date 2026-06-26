# Retrospective: Stewardship Horizon-Scan Cadence Automation (D4)

**Plan:** `~/.claude/plans/2026-06-25-stewardship-horizon-scan.md`
**Commit:** `2f878e8` (`feat(stewardship): horizon-scan cadence automation (D4, #7) (#14)`)
**Date:** 2026-06-25

## Outcome

Shipped `stewardship@1.2.0`: the nightly steward now runs a third deterministic step, `horizon_scan_schedule.py`, that surfaces a "horizon-scan DUE" reminder when the monthly interval elapses. The key reconciliation is honest about a hard constraint — `orchestration:horizon-scanning` is pure Claude reasoning (web search + VRAM judgment + load tests) and cannot run headless, so the steward *reminds and schedules* rather than *executes*. The reminder loop closes when the interactive scan calls `horizon_scan_schedule.py --mark-done`. Wired into all three platform schedulers (Task Scheduler / cron / launchd), with a `{{HORIZON_SCAN_SECTION}}` briefing token set up for D5. 11 tests, 100% coverage; PR #14 squash-merged; `stewardship-v1.2.0` reconciled to the squash commit.

## What worked

- **Premise-first exploration before planning.** The two Explore agents surfaced that horizon-scanning has no backing script and runs load tests — i.e. it *cannot* run headless — *before* any plan was written. That turned the design into a clean brainstorming fork ("reminder vs. headless auto-exec vs. both"), and the user picked the reminder. Without that, the obvious-but-wrong plan (`claude -p` every night) would have shipped a silent-failure surface.
- **Clock injection (`--now ISO8601`) for time-based TDD.** Every cadence test passes a frozen clock; zero real-clock flakiness, and the one real-`datetime.now()` branch is covered by a single no-`--now` test. 100% coverage with no `pragma` beyond `__main__`.
- **Mirroring `drift_check.py`'s idiom** (argparse, dataclass, markdown-default + `--json`, section-marker-from-wrapper) made the new script drop into the existing steward with no new conventions.
- **`release.py` scope discipline held.** The cross-plugin edit used `docs(orchestration):`, so the dry-run bumped `stewardship` only — orchestration stayed put. Verified before `--apply`.
- **Inline tag reconciliation.** Re-pointed `stewardship-v1.2.0` to the squash commit immediately post-merge; `release.py --dry-run` confirmed "nothing to do" — the D6 #11 orphan pattern pre-empted, not deferred.

## Friction / bugs

- **Safety classifier outage blocked the plan-file write mid-planning**
  - *What happened:* Three consecutive `Write` calls for the plan file failed with "claude-opus-4-8 temporarily unavailable, auto mode cannot determine safety."
  - *Root cause:* Transient unavailability of the auto-permission-mode safety classifier (not the action itself).
  - *How caught:* Explicit tool error; read-only tools kept working.
  - *Fix:* Preserved the full plan in context, surfaced the design summary to the user so nothing was lost, retried on confirmation — succeeded immediately.
  - *Rule:* When the auto-mode classifier is down, don't abandon work — read-only ops continue; hold the artifact in context and retry the write. Chained `sleep` to "wait it out" is blocked by the harness, so retry on the next turn rather than polling.

- **Plan's "might break test_init.py" guard was a no-op (but cheap insurance)**
  - *What happened:* Step 2.1 flagged that adding a third script to the cron command might break `test_init.py`.
  - *Root cause:* `test_init.py` only exercises the no-crontab *safe-degradation* path; it never asserts the command string.
  - *How caught:* Read the test first (per the plan's own guard) before editing `init.sh`.
  - *Fix:* None needed — confirmed no-op.
  - *Rule:* A plan that names "this edit might break test X" should make "read X first" an explicit step; the read is cheap and converts an unknown into a confirmed no-op.

- **Plan-mode marker keyed to the stale umbrella-plan path (recurring)**
  - *What happened:* ExitPlanMode again saved/echoed the old D1 umbrella plan (`this-design-looks-right-precious-squid.md`); the real D4 plan lived at a dated path, and no pending retro marker was created for the D4 slug.
  - *Root cause:* Plan mode binds to one tracked plan-file; writing a fresh dated file (correct, to avoid clobbering completed records) diverges from it. Same finding as D3.
  - *How caught:* Known from D3; drove `/plan-completion` and `/plan-retrospective` by explicit path.
  - *Rule (confirmed, now twice):* For each new wave, write the plan to a fresh dated path, accept the marker won't auto-create, and drive completion/retro by explicit path. This is now a stable pattern across D3 + D4, not a one-off.

## Concrete improvements

- **ADR-0010 records the "reminds, not executes" rationale** — so the next maintainer doesn't re-attempt headless execution. Lives at `docs/adr/0010-horizon-scan-cadence-reminder.md`. Done.
- **`--mark-done` wired into the scan skill itself**, not just documented — the cadence loop actually closes after an interactive scan (`orchestration/.../horizon-scanning/SKILL.md` closing step). Done.
- **D4/D5 boundary made concrete** via the `{{HORIZON_SCAN_SECTION}}` token in `morning-briefing.md` — D5's renderer has a defined slot to fill. Done; de-risks D5.
- **Rollout note surfaced** — the live nightly steward runs a previously-generated wrapper; picking up the new step needs a `register_nightly.ps1` re-run (Windows) / cron re-install / launchd reload. Pending user action (out of repo scope).
