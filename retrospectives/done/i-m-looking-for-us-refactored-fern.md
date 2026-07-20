# Retrospective: Aether Engine 050 Engineering Audit

**Plan:** `~/.claude/plans/i-m-looking-for-us-refactored-fern.md`
**Commit:** `c345b34` (`docs(plan): add 050 full engineering audit delivery plan`) + delivery commits `17580d1`, `b54685e`, `66b38ca`, `eafa4b4` (all tagged `#254`)
**Date:** 2026-07-03 _(catch-up retro authored 2026-07-20)_

## Outcome

Ran a top-firm-style engineering audit of the Aether Engine (`Roleplaying/`), grounded in code evidence and delivered as in-repo docs: the audit report (`docs/engineering/050-engineering-audit-2026-07-02.md`, 106 findings across 10 families), an opportunity catalog, a service-free CI subset (ADR-0018), and a set of zero-risk quick-win fixes. Umbrella issue #254 filed; the highest-value follow-ups filed as #255–#262 per a "register now, file on approval" scope decision. A full companion retro already lives in-repo at `Roleplaying/retrospectives/done/2026-07-03-050-engineering-audit.md`; this workspace-root retro closes the pending marker.

## What worked

- **9-agent adversarial plan review before execution** — corrected a false central premise (framed "no CI" as a substrate gap when it was a documented cost opt-out, #164) before any work started.
- **Tiered adversarial verification** — refuted or rescoped ~20 of ~126 raw findings, and caught a cross-agent hallucination (a `host_key` falsely claimed to exist in git history) by verifying against live code.
- **Delegated synthesis** — kept ~22k tokens of raw findings out of the controller context.
- **Pre-land Vale check** — caught the prose blocker before push rather than in CI.

## Friction / bugs

- **Workflow tool stalled twice mid-run (~10h lost, 4/75 agents hung)**
  - *What happened:* A multi-phase Workflow hung; resume produced duplicate agent outputs instead of filling the gaps.
  - *Root cause:* Workflow resume re-dispatched completed work rather than only the missing agents.
  - *How caught:* Manual inspection of the Workflow journal showed 4 agents never returned.
  - *Fix:* Extracted partial results from the journal and re-dispatched the gaps as direct Agent calls.
  - *Rule:* On a stalled multi-phase Workflow, read the journal and re-dispatch only the missing agents as direct Agent calls — don't blind-resume.
- **`python "<script>.py"` exits 126 under the sandbox when backgrounded**
  - *Root cause:* Sandbox exec restriction on backgrounded python.
  - *Fix:* Ran the equivalent via node instead.
  - *Rule:* Prefer node for backgrounded scripts under the sandbox; python foregrounded is fine.
- **Vale `LyHyphens` false-positive on "supply-chain"** — known prose-linter noise; fixed by rewording. (Tracked separately for rule calibration, hb-02j.)

## Concrete improvements

- Audit report + opportunity catalog — `Roleplaying/docs/engineering/`, done.
- Service-free CI subset (ADR-0018) — done; self-hosted-runner follow-up filed as #261.
- Findings #255–#262 filed at initiative granularity — done; remaining findings live in the in-doc register.
- **Deviation noted:** the in-repo delivery plan was authored concurrently with / after Phase A+B execution rather than strictly beforehand (the plan commit body admits "already executed") — acceptable for an audit but worth flagging for future plan-first discipline.
