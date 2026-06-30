# Retrospective: hb-26v Track B — Local PoC-Authoring Viability

**Plan:** `sec-research/docs/superpowers/plans/2026-06-30-hb-26v-track-b-poc-authoring.md`
**Commit:** `6b04de7` (`docs(sec-research): hb-26v Track B verdict — local 7B PoC-authoring not viable (qwen 0/5)`)
**Date:** 2026-06-30

## Outcome

Measured whether local 7B models can author a *working differential PoC* (not just a seed-complete
hypothesis). They cannot: qwen2.5-coder-7b scored **0/5 verified**, authoring semantically-wrong
ReDoS PoCs; deepseek-r1-7b was blocked by a pre-existing sandbox crash. Verdict: the nightly loop is
**local seed-authoring (viable, hb-0vq) + Claude PoC-authoring**. hb-26v closed; harness-robustness
follow-up filed (`hb-dfu`).

## What worked

- **Probe-first scoping.** Task 0's smoke showed the oracle was ~10 s/trial (not the feared minutes),
  and qwen's 0/5 made the full-fleet matrix (Task 3) correctly unnecessary — the verdict landed on a
  cheap 2-tier probe instead of a blind 5-model sweep.
- **Systematic debugging over guessing.** A `0.00` rate with `error` verdicts is ambiguous; dumping
  the raw PoC + the full verdict result (`reason: differential affected-indeterminate`, 4 clean oracle
  phases) pinned the cause precisely: the model detects ReDoS via a thrown exception, but CVE-2022-3517
  *hangs* — so affected and fixed produce identical output. That's a model defect, provable, not a hunch.
- **The verdict-trust split (error vs refuted, hb-be9) made the diagnosis legible** — `error` correctly
  meant "the oracle could not establish the affected signature," not "the model was refuted."

## Friction / bugs

- **The `error` bucket conflates two very different failures.**
  - *What happened:* qwen's `error`s were model-quality (non-discriminating PoC); deepseek's was an
    infra crash (`FileNotFoundError`). Both surface as `error` in the Track-B counts.
  - *How caught:* dumping raw output (model case) + reading the traceback (infra case).
  - *Fix:* none in-band; noted. The recurring lesson (also seen in Track A's all-zero buckets) is that
    an aggregate "error/incomplete" count hides the actionable distinction.
  - *Rule:* a measurement's failure buckets must separate *model* failures from *infra* failures —
    otherwise a 0.00 rate can't be acted on without a manual raw-output dive every time.

- **Pre-existing sandbox crash kills the whole eval (`hb-dfu`).**
  - *What happened:* deepseek trial 0 raised `FileNotFoundError` on the affected work-dir's
    `package.json` (uncaught in the verify/sandbox path, untouched by this work) → the eval process died,
    so deepseek could not be measured at all.
  - *Root cause:* the differential harness isn't resilient to a missing/failed install work dir for a
    given model's PoC-plan shape; a single bad trial aborts the run instead of becoming an `error` verdict.
  - *Fix:* `hb-dfu` — catch the failure per trial (→ error verdict) rather than crashing; then re-probe.

- **Standalone diagnostic import failed** (`from lib import ledger`) — `lib` is `hooks/lib`, and the eval
  bootstraps *both* `scripts/` and `hooks/` onto `sys.path`. Minor; fixed by mirroring that bootstrap.

## Concrete improvements

- **`hb-dfu`** — harden the differential verify harness against the work-dir `FileNotFoundError` (per-trial
  error, not a process crash) + re-probe deepseek-r1-7b Track B. Status: open (P3).
- **Verdict recorded** — nightly loop = local-seed + Claude-PoC; the local-authoring arc (Track A viable,
  Track B not) is now fully measured and documented in the hb-0vq verdict doc. Status: done (commit 6b04de7).
- **Carried:** prompt-hardening for local PoC shape (optional), and the recurring "separate model-vs-infra
  failure buckets" lesson for the eval harness.
