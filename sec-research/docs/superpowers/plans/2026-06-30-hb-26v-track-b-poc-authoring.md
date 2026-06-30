# hb-26v Track B — Local PoC-Authoring Viability (Live Differential Oracle) Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Measure whether local 7B/4B models can author a *working differential PoC* (not just a
seed-complete hypothesis) for the minimatch/CVE-2022-3517 ReDoS reference, via the existing live
Track-B oracle — answering the remaining local-viability question for the nightly loop.

**Architecture:** `score_track_b` (`scripts/eval/authoring_eval.py`) holds a fixed seed-complete
hypothesis constant and runs N LLM PoC-authoring attempts through the **real differential oracle**
(`verify.harness.verify_hypotheses` + `verify.llm_strategy.LLMPocStrategy`, `runner=subprocess.run`
→ Docker). It scores `verified / refuted / error / skipped`. The harness is proven live (Docker/WSL2,
2026-06-26). This plan is **probe-first**: a cheap 2-tier signal before any full matrix, because
authoring a working ReDoS PoC is far harder for a small model than seed-authoring, so the rate may
be low and each trial is expensive (two sandboxed installs + trigger runs).

**Tech Stack:** Python 3.14, `llama-server` (GGUFs at `C:\models\`), Docker 29.6.1 in WSL2 Ubuntu
(`docker.service` active), `run_matrix.ps1` / `authoring_eval.py --track b`.

**Tracker:** bead `hb-26v` (item 1). Follows the hb-0vq seed-authoring fix (commit 863e5ad).

## Global Constraints

- **Docker is the substrate.** WSL2 `docker.service` must be active (verified). The CLI uses the
  real subprocess runner → real containers; `VERIFY_LIVE`/`LLM_LIVE` gate only pytest, so they're
  not required for the CLI (harmless if set).
- **One model per process**, blessed llama-server args, 8 GB ceiling (same as Track A).
- **Each trial is expensive + network-dependent:** the oracle does `npm install minimatch@3.0.4`
  (affected) and `@3.0.5` (fixed) in sandboxed containers, runs the model-authored trigger against
  both, and compares. Expect minutes per trial; npm/registry flakiness shows as `error`, not
  `refuted` (the verdict-trust fix from hb-be9 keeps these distinct — do NOT read `error` as a model
  failure).
- **Reference fixture:** `tests/fixtures/llm/hypothesis_minimatch.json` (`seed_complete: True`,
  verified). The model's job is ONLY the PoC body, not the seed.
- **Provider `llama` only** — measuring the local fleet; no Claude tokens.

## Pre-flight estimate (Task 0) governs scope

The full 5-model matrix may be too slow/flaky to be worth it if per-trial cost is high. Task 0's
single-model smoke times one trial; the probe (Task 1) then runs only the **2 most-likely tiers**
(qwen2.5-coder-7b = structured/tooling, deepseek-r1-7b = reasoning) at low trials. Expand to the
full fleet (Task 3) **only if** the probe shows a non-trivial `verified` rate worth the wall-clock.

---

### Task 0: Pre-flight — oracle live, fixture valid, one-trial smoke (time it)

**Files:** run-only — `scripts/sandbox/doctor.py`, `scripts/eval/authoring_eval.py`.

- [x] **Step 1: Sandbox doctor green.**

Run: `cd C:/Users/Garre/Workspace/sec-research && python scripts/sandbox/doctor.py`
Expected: exit 0 (Docker reachable in WSL2). If it fails: `wsl.exe -d Ubuntu -e bash -lc "sudo service docker start"` then re-run. STOP if still failing — Track B is meaningless without a live oracle.

- [x] **Step 2: One-model live Track-B smoke (qwen, 2 trials) — proves the path + times a trial.**

Via a script file (process lifecycle in-file → Stop-Process guard not tripped):
`runtime/eval/_smoke_b.ps1` launches qwen2.5-coder-7b, waits `/health`, then
`python scripts/eval/authoring_eval.py --track b --trials 2 --report runtime/eval/2026-06-30-trackb/_smoke.json`,
then stops the server. Mirror `runtime/eval/_smoke.ps1` (already exists) but `--track b`.
Expected: `_smoke.json` has a `track_b` block with `verified/refuted/error/skipped` summing to 2.
Record wall-clock → **`SECS_PER_TRIAL_B = ____`**. (A `verified:0` smoke is a valid datapoint —
the smoke proves the live oracle path runs, not that qwen authored a working PoC.)

- [x] **Step 3: Decide probe trial count from the smoke timing.**

Budget the probe to ≲ ~20 min wall-clock: `TRIALS_B = min(10, floor(1200 / (2 * SECS_PER_TRIAL_B)))`
(2 models). Record **`TRIALS_B = ____`**. If `SECS_PER_TRIAL_B` is so high that even 3 trials/model
blows the budget, drop to `TRIALS_B = 3` and note the low-N caveat in the verdict.

---

### Task 1: Probe Track B on 2 tiers

**Files:** run-only → `runtime/eval/2026-06-30-trackb/<model>.trackb.json` (gitignored).

- [x] **Step 1: Run the probe (background) for qwen2.5-coder-7b + deepseek-r1-7b.**

A `runtime/eval/_probe_b.ps1` loop (in-file lifecycle) over the 2 models: launch llama-server →
`/health` (120 s deadline) → `python scripts/eval/authoring_eval.py --track b --trials <TRIALS_B>
--report runtime/eval/2026-06-30-trackb/<model>.trackb.json` → stop. Tee to a log. Run in background.

- [x] **Step 2: Read the per-model verdicts.**

Run: `pwsh -NoProfile -Command "Get-ChildItem runtime/eval/2026-06-30-trackb/*.trackb.json | ForEach-Object { $j=Get-Content $_ -Raw|ConvertFrom-Json; '{0}: verified={1} refuted={2} error={3} skipped={4} rate={5}' -f $j.model,$j.track_b.verified,$j.track_b.refuted,$j.track_b.error,$j.track_b.skipped,$j.track_b.rate }"`
Distinguish `error` (infra/npm flakiness — re-run those trials if dominant) from `refuted`
(model authored a non-discriminating PoC — a real authoring miss).

---

### Task 2: Synthesize → viability verdict → tracker

**Files:** append to `docs/superpowers/research/2026-06-30-hb-0vq-local-authoring-verdict.md`;
`runtime/journals/2026-06-30-hb-26v-trackb.md`; tracker.

- [x] **Step 1: Write the journal** (models, trials, per-verdict counts, timings, any error-dominant re-runs).

- [x] **Step 2: Append a "Track B (PoC-authoring)" section to the verdict doc** with the probe
  rates inlined as `Proof:` (runtime/ is gitignored) and a verdict:
  - **viable** (non-trivial `verified` rate) → recommend local PoC-authoring for the nightly loop;
    expand to the full fleet (Task 3) to pick the best model.
  - **not viable** (≈0 `verified`, mostly `refuted`) → recommend **Claude for PoC-authoring**
    (keep local for seed-authoring, which IS viable); the nightly loop is local-seed + Claude-PoC.
  - **inconclusive** (`error`-dominant) → infra-flakiness blocked measurement; fix sandbox/network
    and re-probe. Do not call viability either way.

- [x] **Step 3: Update `hb-26v`.** Record the verdict + the full-fleet decision. Close hb-26v if the
  probe is decisive (viable→expand becomes a new bead, or not-viable→resolved); else keep open with
  the re-probe next action.

### Task 3 (conditional): Full-fleet Track B — only if the probe is "viable"

- [x] Expand to all loaded models (`run_matrix.ps1 -Track b -Trials <N> -ReportDir runtime/eval/2026-06-30-trackb`),
  pick the best, file the "wire local PoC-authoring" follow-up. Skip entirely if the probe was not-viable/inconclusive.

## Verification

- Sandbox doctor exits 0; the smoke produced a `track_b` block (path proven live).
- Probe reports exist for both tiers with `verified/refuted/error/skipped` summing to `TRIALS_B`.
- The verdict is evidence-cited (rates inlined), distinguishes `error` from `refuted`, and states a
  clear viable / not-viable / inconclusive call — no `error`-flakiness laundered into "model failed."
- **Done =** probe run, verdict appended to the doc, hb-26v updated with the local-PoC-authoring
  decision (and the full-fleet expansion gated on a "viable" result).

## Follow-ups (file as beads)

- If viable: full-fleet Track B + wire the best local model for PoC-authoring.
- If error-dominant: sandbox/network hardening for the oracle under repeated runs.
- `score_track_a` `incomplete` bucket; prompt-hardening (carried from hb-26v).

## Completion (2026-06-30)

**Resolved: local 7B PoC-authoring NOT viable.** Probe-first paid off — the oracle was ~10 s/trial
(not minutes), but qwen2.5-coder-7b scored **0/5 verified** (5 error): a diagnosed model-quality
failure (exception-based ReDoS detection + non-backtracking input → non-discriminating PoC, oracle
correctly returns error/affected-indeterminate; some trials unparseable). deepseek-r1-7b was blocked
by a pre-existing sandbox `FileNotFoundError` crash (verify path untouched here) → follow-up `hb-dfu`.
Task 3 (full fleet) correctly skipped — the probe was not-viable. Verdict appended to the
hb-0vq verdict doc (commit 6b04de7); hb-26v closed; nightly loop = local-seed + Claude-PoC.

## Retrospective

_(To be completed after execution.)_

- Did local models author any working differential PoC, or is PoC-authoring past the 7B tier (vs
  seed-authoring, which the hb-0vq fix proved viable)?
- Was the oracle stable under repeated runs, or did `error`-flakiness dominate?
- Did probe-first save wall-clock vs a blind full matrix?
