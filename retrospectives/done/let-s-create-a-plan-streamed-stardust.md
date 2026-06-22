# Retrospective: device.state.changed lifecycle producer (System.Control)

**Plan:** `~/.claude/plans/let-s-create-a-plan-streamed-stardust.md`
**Tracker:** closes hb-09x (does not touch hb-uag)
**Date:** 2026-06-22 (residual close-out via session-recovery pass — tracker hb-bam)
**Outcome:** DONE — all 4 tasks green. `device.state.changed` fires event-driven at
daemon-ready (idempotent) and shutdown; reuses the #179 `STATE_*` dirty-signal loop with
zero new protocol overhead. Producer + consumers + CLI + docstrings + full gate shipped.

## Notes
- `offline` must fire before `self._client` closes — placement at the top of
  `_host_cleanup` is load-bearing. Unlike health, `online` is NOT seeded-silent.
- Zone-count-changed and republish-on-subscribe were explicitly deferred with re-open
  triggers recorded.
