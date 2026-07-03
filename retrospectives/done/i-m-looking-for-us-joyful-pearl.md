# Retrospective: Bring the learning plugin to full working order

**Plan:** `~/.claude/plans/i-m-looking-for-us-joyful-pearl.md`
**Commit:** `932c2b9` (`chore(release): evidence@1.2.1, learning@1.6.0, retrospective@1.2.1, stewardship@1.4.1`) — via PR #52 merge `970ca04`
**Date:** 2026-07-03

## Outcome

The learning plugin's instinct loop, silently broken end-to-end on Windows since install, is fully operational. Shipped learning 1.6.0 + stewardship 1.4.1 (PR #52, closes #51/#40): UTF-8 at every printing entry point (SessionStart surfacing and `/instinct-status` had *never* worked — cp1252 crash swallowed by the fail-open wrapper), dual-bound observation retention (capture cap + nightly compaction; 111 MB → 53 MB on first apply), and a hardened `register_nightly.ps1` (resolved absolute python, marketplace-checkout paths, fail-loud wrapper, validated `-LearningScript`). Machine-local: task re-registered from the marketplace checkout, smoke test produced the first-ever `last_mine_report.json` — 107 instincts written across 4 projects. ADR 0014 records the decisions.

## What worked

- **Manual repro of the exact hook invocation** — piping the SessionStart event into `run_with_flags.py` surfaced the cp1252 crash in one command; the whole diagnosis hinged on not trusting "hooks are registered" as "hooks work".
- **Parallel Explore agents (plugin internals vs live install state)** — the dev-clone view alone said "healthy"; only the live-state audit found the dead scheduler paths and missing mine report.
- **Plan agent grounding before writing the plan** — it corrected two premises (the 110 MB file was all recent, so age-retention alone was a no-op; `register_nightly.ps1` baked the bare python name), both of which would have shipped a wrong design.
- **Adversarial review earned its keep** — the marker re-nesting bug (idempotency of `cap_tool_response`) and the unquoted spaced-python-path would both have failed silently at 03:00, the precise failure class being fixed.
- **Fail-loud wrapper validated itself on the smoke test** — exit 1 from `drift_check`'s designed stale-context signal proved LastTaskResult now carries real information.

## Friction / bugs

- **Fail-open hook wrapper hid a total feature outage for weeks**
  - *What happened:* `surface.py` crashed on every SessionStart; wrapper printed to stderr and exited 0; nothing ever surfaced and nobody noticed.
  - *Root cause:* deliberate fail-open design with no error sink anyone reads.
  - *How caught:* manual invocation of the exact hook command during the audit.
  - *Fix:* UTF-8 fix shipped; observability follow-up is bead hb-rap; systemic wrapper UTF-8 is hb-zxg.
  - *Rule:* When auditing a hook-based feature, run the hook's exact command line manually and read stderr — registration + green sessions prove nothing.
- **Repo relocation silently killed the scheduled task for 3 nights**
  - *What happened:* the Jun 30 move of claude-marketplace to Workspace/ broke every baked path in `run-nightly.ps1`; log errors then degraded to empty output when bare-name `python3` resolution changed.
  - *Root cause:* scheduler wrapper baked dev-clone paths + unresolved interpreter name.
  - *How caught:* reading `nightly.log` history during the audit.
  - *Fix:* marketplace-checkout paths + `(Get-Command).Source` + fail-loud exit; shipped in stewardship 1.4.1.
  - *Rule:* Moving a repo requires a scheduled-task audit (`Get-ScheduledTask | % Actions` grep for the old path) as part of the relocation runbook.
- **Test seeds diverged from real data shape**
  - *What happened:* nightly test seeds used `timestamp: 1.0` (1970) and missing timestamps; new compaction correctly deleted them, breaking the idempotency test.
  - *Root cause:* seeds hand-rolled rather than mirroring `observe.py`'s invariant (always stamps `time.time()`).
  - *How caught:* reasoning about the compaction cutoff before running; fixed seeds pre-emptively.
  - *Rule:* Test fixtures should preserve producer invariants (every record has a fresh timestamp), or new consumers of those invariants will "break" tests that were never realistic.

## Concrete improvements

- **ADR 0014** (`docs/adr/0014-learning-loop-windows-repair.md`) — decisions + rejected alternatives; done.
- **Beads filed:** hb-zxg (systemic run_with_flags UTF-8 + vendored re-sync), hb-rap (hook-error observability), hb-168 (tool_input capture cap — residual ~50 MB is Write/Edit payloads); pending.
- **Stale context files surfaced by the smoke test** (`memory-sync.md`, `user-persona.md`, 55d unverified) — the fail-loud steward will keep flagging until refreshed; follow-up for a maintenance pass.
- **Auto-memory** `project_learning_plugin_repair.md` written (data-root location, hook-audit rule, scheduler-path rule).
