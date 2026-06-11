# Retrospective: Career/ Re-engineering (career-ops nested private repo)

**Plan:** `~/.claude/plans/the-workspace-directory-career-giggly-narwhal.md`
**Commit:** `eb4ca19` (`docs: record cloud-probe verdict — Mode C adopted`) — career-ops repo
**Date:** 2026-06-11

> Canonical retro (full domain detail) lives in the private repo:
> `Career/docs/retrospectives/2026-06-11-reengineering-plan.md`. This copy carries only
> the harness-level findings safe for the public Workspace repo.

## Outcome

Seven phases (P0–P6) delivered in one overnight arc inside `Career/` (nested private
repo; ADR-003 keeps it out of this public repo's index). Event-sourced tracker,
YAML-mastered resume pipeline with an ATS keyword-fidelity gate, single-file dashboard,
tailoring skill, public hire page (`site/content/hire/` → live), and a local nightly
build task. The cloud scheduled routine was **not** registered: all three capability
probes failed silently → Mode C (interactive sweeps + local Task Scheduler).

## What worked (harness-level)

- **Adversarial multi-lens review before execution** — five Workflow critics reshaped
  the plan (event-sourcing, probe-to-P0, idempotent outbound); execution then hit zero
  architectural surprises. Second plan in a row where this paid for itself.
- **Probe-before-register for cloud routines** — three escalating one-time probes
  (ending with a deliberately minimal haiku probe whose silence was unambiguous)
  prevented registering a daily cloud routine that would have no-opped forever.
- **Verification gates over trust** — the pdfplumber ATS gate caught a real PDF
  line-break hazard on first use; the fix went into the template, not into loosening
  the matcher.

## Friction / bugs

- **Headless cloud sessions lack interactively-authenticated MCP connectors**
  - *What happened:* scheduled cloud runs produced zero artifacts and zero errors.
  - *Root cause:* claude.ai-authenticated connectors (e.g. Gmail) are absent in
    headless runs; private-repo sources also failed to provision. Failures are silent.
  - *How caught:* triple-probe ladder with a minimal final probe.
  - *Rule:* never register a scheduled cloud routine until a one-time probe proves the
    minimal capability end-to-end; silence past fire + 15 min = failure.
- **Embedded-template name collisions** — a Typst loop var shadowed the builtin `h()`;
  Jinja `x.items` resolved the dict method. *Rule:* no single-letter loop vars in
  Typst; `[]` access for dicts in Jinja.
- **GateGuard fact-forcing fired on nearly every first Write of a new file** — high
  per-edit cost during a greenfield build (facts often degenerate to "nothing imports
  this yet"). It did enforce one useful Glob-duplicate check. Possible tuning:
  exempt paths that don't exist yet in repos younger than N days, or honor a
  plan-approved manifest.
- **Hookify `Stop-Process -Force` regex over-matched** — `\bStop-Process\b[^|]*-Force\b`
  also caught a `Move-Item -Force` later on the same line; worked around with
  `taskkill`. Worth a regex tighten in the hookify rule.

## Concrete improvements

- **Deferred capabilities filed as career-ops issues #8/#9** (weekly intel refresh,
  interview-prep skill) — in-repo project work stays on GitHub issues per backlog
  convention; epic bead hb-yjn closes with this retro.
- **Re-probe trigger documented** in the private repo's ADR — if cloud routines gain
  connector auth or private-repo sources, re-run the probe ladder before registering.
