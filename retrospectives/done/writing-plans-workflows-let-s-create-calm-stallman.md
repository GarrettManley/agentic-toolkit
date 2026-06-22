# Retrospective: Evidence-based hardware-upgrade dashboard

**Plan:** `~/.claude/plans/writing-plans-workflows-let-s-create-calm-stallman.md`
**Tracker:** hb-62n
**Date:** 2026-06-22 (residual close-out via session-recovery pass — tracker hb-bam)
**Outcome:** DONE — built end-to-end and **recovered/committed in `23530eb`** after the
original session exited before committing. 3-layer architecture: 6-member agent team +
dynamic Workflow, Python collector + stdlib-OLS analytics, FastAPI local API, Vite/React/TS
WCAG-AA SPA. Schemas-first (Draft 2020-12), real machine profile via `detect_machine.ps1`,
all test suites green offline.

## Notes
- Cold-start honesty is by design: day-1 forecasts are low-confidence (history-scaled
  confidence ramp) — don't "fix" it into implying precision the data can't support.
- Price time-series + computed analytics are per-machine runtime (gitignored); only source
  + curated component/seed/sku records are tracked. This recovery pass is what made the
  untracked build durable — the exact failure mode the new protocol (hb-bam) prevents.
