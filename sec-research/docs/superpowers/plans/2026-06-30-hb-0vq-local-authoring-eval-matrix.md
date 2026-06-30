# hb-0vq: Local-Model Authoring Reliability — Live Eval Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Measure local GGUF authoring reliability (seed-completeness, then PoC-authoring only if warranted) across the model fleet with the existing eval harness, then resolve hb-0vq with an evidence-backed local-viability verdict.

**Architecture:** The eval harness (`scripts/eval/authoring_eval.py`, `scripts/eval/run_matrix.ps1`) already exists and is offline-proven (Phase 0, commit `4a33016`). This plan is **empirical-first** (operator-chosen 2026-06-30): run **Track A (seed-completeness) across the fleet first**; only if a model clears the seed bar do we stand up Docker and run the heavier **Track B (PoC-authoring through the differential oracle)**. Then write a decision artifact and update trackers. **No production code is added** — the value is the evidence and the decision. (A `summarize_matrix.py` aggregator was considered and cut as YAGNI: ranking ≤5 numbers is a one-time manual read.)

**Tech Stack:** Python 3.14, `pytest`, `llama-server` (llama.cpp) at `C:\llama\llama-server.exe`, GGUFs at `C:\models\`, Docker 29.6.1 in WSL2 Ubuntu (Track B only), PowerShell 7.6 for the matrix runner.

**Tracker:** bead `hb-0vq` (P2). Parent: the hb-322 supervised-run plan (`writing-plans-let-s-write-a-glimmering-salamander`) locked "Claude now, local later"; this plan resolves the "local later" half with data.

### Why this is worth doing (value + do-nothing baseline)

- **Do-nothing baseline:** if this plan never runs, **hb-322 (P1) proceeds unchanged via Claude** — Claude is already the default, fully-wired authoring provider and works. So hb-0vq is **not a hard blocker** on hb-322; bd's `blocks` edge reflects the *local* path only.
- **The real driver for local authoring:** the workspace's purpose is a **nightly, self-improving, automated** bug-bounty loop. Every nightly authoring call via Claude burns API tokens; a viable local authoring path makes the loop **free to run continuously** and **API-independent**. That is the named consumer this evidence serves.
- **What the verdict buys:** either (a) a local model good enough to wire as the nightly authoring default (token savings), (b) a measured gap that justifies the deterministic-scaffolding build, or (c) a defensible "Claude-only for now" decision that **clears the stale hb-0vq blocker bookkeeping** on hb-322 with evidence rather than assumption. All three are wins; the cost of inaction is an unresolved local-vs-cloud question that keeps the nightly loop either token-spending or manually gated.

## Global Constraints

- **One model per process.** Serialize loads, free VRAM between models. `run_matrix.ps1` enforces this (`Stop-Process` in `finally`). Never two servers at once — 8 GB ceiling.
- **Blessed llama-server args (verbatim):** `--ctx-size 8192 --n-gpu-layers 99 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --seed 42`. `--flash-attn` requires the explicit `on` value.
- **No program scope required.** The eval is fixture-based (`tests/fixtures/llm/recon_item_minimatch.json`) and the local provider hits loopback (`127.0.0.1:8080`), in `LLAMA_BOOTSTRAP_HOSTS` — PT-1 will not block. Do NOT load a program scope; this is not recon.
- **Pin the report dir on every run.** Always pass `-ReportDir runtime/eval/2026-06-30` so a run that slips past midnight does not split across two date dirs (`run_matrix.ps1` defaults to `Get-Date`).
- **One report file per (model, track).** `authoring_eval.py` does `write_text` (no read-merge), so a second `--track` pass to the same path **overwrites** the first. Track A and Track B therefore write **distinct** paths (`<model>.json` vs `<model>.trackb.json`).
- **Evidence discipline.** `runtime/` is gitignored — per-model JSONs are NOT committed. The decision artifact MUST inline the load-bearing rates as `Proof:` and `Citation:` the harness, so the claim survives without the gitignored files.
- **Reference target fixed:** minimatch / CVE-2022-3517 (the Phase 0 reference) — all models author against the same fixtures, so cross-model numbers are comparable.
- **Provider is `llama` only.** This measures the *local* fleet; spend no Claude tokens.
- **Prior evidence (hb-0vq notes, 2026-06-27):** `qwen2.5-coder-7b` and `gemma-4-E4B` already produced **0 reliable hypotheses** in a prior run. The matrix re-confirms those two and adds first measurements for the **3 untested models** (`deepseek-r1-7b` reasoning, `gemma3-4b`, `phi4-mini`) — that is where the wall-clock buys new signal.

### Thresholds (provisional — the verdict interprets, it does not mechanically apply)

- `seed_bar = 0.8` (Track A seed-completeness), `poc_bar = 0.5` (Track B verify rate). These are **starting bars, not law.** The consumer is an **unattended nightly loop**: a low seed rate means silent false-nulls (the exact hb-322 anti-slop risk), so the bar is high *for the unattended case*. A retry-tolerant or human-gated consumer could accept lower — the decision artifact (Task 3) states the observed rates and argues the bar, rather than rubber-stamping 0.8/0.5.

---

### Task 0: Pre-flight — harness green, prerequisites present, one-model live smoke

**Files:** Run-only — `scripts/eval/authoring_eval.py`, `tests/scripts/test_authoring_eval.py`, `tests/scripts/test_nightly_supervised.py`, `scripts/eval/run_matrix.ps1`.

- [x] **Step 1: Offline eval suite green** (proves the scorer isn't broken before measuring with it).

Run: `cd C:/Users/Garre/Workspace/sec-research && python -m pytest tests/scripts/test_authoring_eval.py tests/scripts/test_nightly_supervised.py -q`
Expected: all pass (offline, no GPU). If red, STOP — the harness regressed.

- [x] **Step 2: Prerequisites physically present.**

Run: `pwsh -NoProfile -Command "Test-Path C:\llama\llama-server.exe; 'qwen2.5-coder-7b-Q4_K_M.gguf','deepseek-r1-7b-Q4_K_M.gguf','gemma-4-E4B-it-Q4_K_M.gguf','gemma3-4b-Q4_K_M.gguf','phi4-mini-Q4_K_M.gguf' | ForEach-Object { [pscustomobject]@{ Model=$_; Present=(Test-Path \"C:\models\$_\") } }"`
Expected: `llama-server.exe` True and all 5 models Present=True. (Verified 2026-06-30; re-confirms at exec time.)

- [x] **Step 3: Pre-create the report dir** (Tee-Object does not create parents).

Run: `pwsh -NoProfile -Command "New-Item -ItemType Directory -Force runtime/eval/2026-06-30 | Out-Null"`

- [x] **Step 4: One-model live Track-A smoke (2 trials) — proves live wiring with a bounded health wait.**

This is a manual single-model launch (NOT `run_matrix.ps1`, which loops all 5). The `try/finally` guarantees the server is killed even if `authoring_eval.py` throws — a leaked server on port 8080 makes **every** Task 1 model report "never became healthy" and get silently skipped:
```powershell
$srv = Start-Process -PassThru -WindowStyle Hidden "C:\llama\llama-server.exe" -ArgumentList @("-m","C:\models\qwen2.5-coder-7b-Q4_K_M.gguf","--ctx-size","8192","--n-gpu-layers","99","--flash-attn","on","--cache-type-k","q8_0","--cache-type-v","q8_0","--seed","42")
try {
  $deadline = (Get-Date).AddSeconds(120)
  do { Start-Sleep 2; $ok = try { (Invoke-RestMethod http://127.0.0.1:8080/health).status -eq "ok" } catch { $false } } until ($ok -or (Get-Date) -gt $deadline)
  if (-not $ok) { throw "server never healthy" }
  $env:SECRESEARCH_LLM_PROVIDER="llama"; $env:SECRESEARCH_LLAMA_MODEL="qwen2.5-coder-7b-Q4_K_M.gguf"
  python scripts/eval/authoring_eval.py --track a --trials 2 --report runtime/eval/2026-06-30/_smoke.json
} finally { Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue }
```
Expected: `_smoke.json` exists with `provider:"llama"`, `model`, and a `track_a` block (`trials:2`, buckets). A `0`/all-`empty_seed` result is a **valid** datapoint (the hb-0vq symptom) — the smoke proves the path runs, not that the model succeeds. No commit.

- [x] **Step 5: Choose the Track-A trial count from the smoke timing.**

Note the smoke wall-clock. Full Track A ≈ 5 × (cold-load ≈ 40 s + Trials × per-trial-seconds). **Rule:** if per-trial > 90 s, use `-Trials 10`; else `-Trials 20`. Record the chosen value here for Task 1: **`TRIALS_A = ____`**.

---

### Task 1: Run Track A across the fleet (seed-completeness; no Docker)

**Files:** Run-only — `scripts/eval/run_matrix.ps1` → writes `runtime/eval/2026-06-30/<model>.json` (gitignored).

- [x] **Step 1: Clear any leaked server + advise on GPU, then launch the Track A matrix (background), pinned report dir, using `TRIALS_A` from Task 0 Step 5.**

First kill any orphaned server (a leaked port-8080 holder makes every model report unhealthy) and advise on free VRAM (OOM under the Windows compositor / a game looks identical to a true ceiling failure in the log — close GPU-heavy apps first):
```powershell
Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
nvidia-smi --query-gpu=memory.used,memory.free --format=csv   # advisory: want most of 8 GB free
```
Run (background): `pwsh -NoProfile -Command "./scripts/eval/run_matrix.ps1 -Track a -Trials <TRIALS_A> -ReportDir runtime/eval/2026-06-30 *>&1 | Tee-Object runtime/eval/2026-06-30/track-a-run.log"`
Replace `<TRIALS_A>` with the recorded value. The runner serializes all 5 models (cold-load → `/health` 120 s deadline → eval → free VRAM). A model that never becomes healthy is logged and skipped (`continue`) — a **real datapoint** (too large / OOM under contention), not a failure.

**Re-run note (idempotency):** `run_matrix.ps1` re-runs all 5 models and **overwrites** their JSONs. With the blessed fixed `--seed 42` a clean re-run reproduces the same rates, but a model that succeeded then OOMs on a retry would have its good JSON clobbered — before any partial-failure retry, copy the good `<model>.json` files aside (or retry only the skipped models via the Task 2 Step 4 manual launch with `--track a`).

- [x] **Step 2: Follow the run to completion.**

Run: `pwsh -NoProfile -Command "Get-Content -Wait runtime/eval/2026-06-30/track-a-run.log"` (Ctrl-C once you see `Reports written to runtime/eval/2026-06-30`). Record any `never became healthy` skips for the journal (Task 3).

- [x] **Step 3: Confirm Track A reports.**

Run: `pwsh -NoProfile -Command "Get-ChildItem runtime/eval/2026-06-30/*.json | Where-Object Name -ne '_smoke.json' | ForEach-Object { $j = Get-Content $_ -Raw | ConvertFrom-Json; '{0}: a={1}' -f $j.model, $j.track_a.rate }"`
Expected: one line per loaded model with numeric `track_a.rate ∈ [0,1]`. Fewer than 5 → which were skipped + why goes in the journal. No commit (gitignored).

---

### Task 2: Decision point → conditional Track B (PoC-authoring through the oracle)

**Files:** Run-only — `scripts/sandbox/doctor.py`; per-model `authoring_eval.py --track b` writing **distinct** `runtime/eval/2026-06-30/<model>.trackb.json` paths.

- [x] **Step 1: Identify models that clear the seed bar.**

Run: `pwsh -NoProfile -Command "Get-ChildItem runtime/eval/2026-06-30/*.json | Where-Object Name -notlike '*trackb*' | Where-Object Name -ne '_smoke.json' | ForEach-Object { $j=Get-Content $_ -Raw|ConvertFrom-Json; if ($j.track_a.rate -ge 0.8) { ($j.model -replace '\.gguf$','') } }"`
This prints the GGUF names of models with `track_a.rate ≥ 0.8` (the `seed_bar`).

- [x] **Step 2 (branch — NO model clears the bar): skip Track B entirely.**

If Step 1 prints nothing (the **expected hb-0vq symptom**), do **not** start Docker — a sub-0.8-seed model is verdict branch (c) regardless of any PoC rate, so Track B is non-signal. Record "no model cleared seed_bar; Track B skipped" in the journal and go to Task 3 with a **branch-(c)** verdict.

- [x] **Step 3 (branch — ≥1 model clears the bar): bring up the sandbox substrate.**

Start the distro AND the Docker daemon (distro start ≠ daemon start), then check the doctor:
```bash
wsl.exe -d Ubuntu -e bash -lc "sudo service docker start && docker info --format '{{.ServerVersion}}'"   # expect 29.6.1
```
Then: `cd C:/Users/Garre/Workspace/sec-research && python scripts/sandbox/doctor.py` → expect exit 0. If the doctor fails, STOP and record — Track B is meaningless without a live oracle.

- [x] **Step 4 (branch — ≥1 model clears the bar): hand-invoke Track B per qualifying model, distinct report paths.**

`run_matrix.ps1` has no model filter, and `-Track b` to the Track-A path would overwrite it — so launch each qualifying model manually and write `<model>.trackb.json`. For each `M` from Step 1:
```powershell
$M = "qwen2.5-coder-7b-Q4_K_M.gguf"   # repeat per qualifying model
$srv = Start-Process -PassThru -WindowStyle Hidden "C:\llama\llama-server.exe" -ArgumentList @("-m","C:\models\$M","--ctx-size","8192","--n-gpu-layers","99","--flash-attn","on","--cache-type-k","q8_0","--cache-type-v","q8_0","--seed","42")
$deadline=(Get-Date).AddSeconds(120); do { Start-Sleep 2; $ok = try { (Invoke-RestMethod http://127.0.0.1:8080/health).status -eq "ok" } catch { $false } } until ($ok -or (Get-Date) -gt $deadline)
$env:SECRESEARCH_LLM_PROVIDER="llama"; $env:SECRESEARCH_LLAMA_MODEL=$M
python scripts/eval/authoring_eval.py --track b --trials 10 --report ("runtime/eval/2026-06-30/{0}.trackb.json" -f ($M -replace '\.gguf$',''))
Stop-Process -Id $srv.Id -Force
```
Track B holds the minimatch/CVE-2022-3517 hypothesis constant and scores whether the model authors a PoC the differential oracle **verifies** — a clean authoring-quality signal. Confirm each `<model>.trackb.json` has a numeric `track_b.rate`. **On any mid-run crash, before retrying:** `wsl.exe -d Ubuntu -e bash -lc "docker container prune -f"` and re-run `python scripts/sandbox/doctor.py` (exit 0) — orphaned containers cause port/stale-mount failures on the next attempt.

---

### Task 3: Synthesize evidence → decision artifact → update trackers

**Files:**
- Create: `docs/superpowers/research/2026-06-30-hb-0vq-local-authoring-verdict.md` (decision + inlined evidence; the `Write` tool creates the parent dir).
- Create: `runtime/journals/2026-06-30-hb-0vq-eval.md` (run journal — what ran, skips, timings; gitignored).

- [x] **Step 1: Create the journal dir and write the run journal.**

Run: `pwsh -NoProfile -Command "New-Item -ItemType Directory -Force runtime/journals | Out-Null"`. Then author `runtime/journals/2026-06-30-hb-0vq-eval.md`: `TRIALS_A` chosen + why, per-model Track-A rates, any health-skips, whether Track B ran (and for which models) or was skipped, total wall-clock.

- [x] **Step 2: Assemble the evidence table (manual read — ≤5 models + ≤N Track-B files).**

Run: `pwsh -NoProfile -Command "Get-ChildItem runtime/eval/2026-06-30/*.json | Where-Object Name -ne '_smoke.json' | ForEach-Object { $j=Get-Content $_ -Raw|ConvertFrom-Json; '{0}: a={1} b={2}' -f $j.model, ($j.track_a.rate ?? 'n/a'), ($j.track_b.rate ?? 'n/a') }"`
Read the rates directly into a small markdown table (model | seed-rate | poc-rate | note) for the artifact.

- [x] **Step 3: Write the decision artifact (inline the numbers — `runtime/` is gitignored).**

Author `docs/superpowers/research/2026-06-30-hb-0vq-local-authoring-verdict.md`:
  - **Question:** can any local GGUF (8 GB ceiling) reliably author seed-complete dependency-cve hypotheses (+ working PoCs) against minimatch/CVE-2022-3517?
  - **Method:** `Citation:` `scripts/eval/authoring_eval.py` + `run_matrix.ps1`; blessed args; `TRIALS_A` (+ Track-B trials); provider `llama`. Label each model **new measurement** vs **re-confirmation** (qwen/gemma-4 = re-confirm).
  - **Results:** the Step-2 table verbatim as `Proof:` (per-model seed/poc rates); note skipped models + why.
  - **Verdict (data picks the branch — do not pre-judge):**
    - **(a)** a model clears both bars → recommend wiring it as the local nightly authoring default + a fuller Track-B confirmation (follow-up bead).
    - **(b)** seed-reliable but PoC-weak → recommend **deterministic advisory pre-selection scaffolding** (mirror `_resolve_fixed_version`) as the next bead, with the measured gap as justification.
    - **(c)** uniformly sub-bar (the expected hb-0vq symptom) → recommend **Claude-only authoring for now**; file a deferred bead to revisit when a stronger local model fits the ceiling.
  - **Impact on hb-322:** state plainly Claude authoring (default) carries hb-322 regardless; this verdict resolves the *local-path* question and clears hb-0vq's blocker bookkeeping with evidence.

- [x] **Step 4: Run the full suite, then commit the artifact.**

Run: `cd C:/Users/Garre/Workspace/sec-research && python -m pytest -q` → expect no regression (~399 collected; this plan adds no code, so green is the baseline).
Then:
```bash
cd C:/Users/Garre/Workspace/sec-research
git add docs/superpowers/research/2026-06-30-hb-0vq-local-authoring-verdict.md docs/superpowers/plans/2026-06-30-hb-0vq-local-authoring-eval-matrix.md
git commit -m "docs(sec-research): hb-0vq local-authoring viability verdict — live eval matrix evidence"
```

- [x] **Step 5: Update the trackers.**

Run: `bd -C C:/Users/Garre/.claude/harness-backlog update hb-0vq --notes "Phase 1 live matrix 2026-06-30: <verdict + best model or 'none cleared seed_bar'>. Doc: sec-research/docs/superpowers/research/2026-06-30-hb-0vq-local-authoring-verdict.md."`
Then per branch: **(c)** → `bd close hb-0vq` (evidence-backed deferral resolves it) + file the deferred-revisit bead; **(a)/(b)** → leave hb-0vq open with the next-action note and `bd create` the follow-up (content from the Follow-ups section). Add an hb-322 note that the local-path blocker is resolved (Claude path stands). Decide close-vs-open from the actual data at exec time.

**Recovery ordering:** the commit (Step 4) precedes this tracker update, so if `bd` fails here, re-run **only** the `bd update`/`close`/`create` commands — do **not** re-commit (the artifact is already landed). `bd update --notes` is append-only, so check `bd show hb-0vq` before re-running to avoid a duplicate note.

---

## Verification

- **Offline harness green** (Task 0 Step 1): `python -m pytest tests/scripts/test_authoring_eval.py tests/scripts/test_nightly_supervised.py -q` passes.
- **Full suite green** (Task 3 Step 4): `pytest -q` no regression (~399 collected). This plan adds no production code, so green is the unchanged baseline — a red result means something external broke and must be triaged before the commit.
- **Live evidence exists:** `runtime/eval/2026-06-30/` holds a `<model>.json` per model that loaded, each with numeric `track_a.rate` (+ `<model>.trackb.json` for any Track-B model). Skips are documented in the journal, not silently dropped.
- **Decision is defensible and self-contained:** `docs/superpowers/research/2026-06-30-hb-0vq-local-authoring-verdict.md` states a verdict whose `Proof:` (rate table) is inlined (survives gitignored `runtime/`), `Citation:` the harness, reproducible via the documented commands.
- **Done =** the verdict artifact is committed, trackers reflect it (hb-0vq resolved-or-next-actioned, hb-322 local-path note), and the local-vs-cloud authoring question is answered with data. No model claimed viable without its rate as proof; no health-skip laundered into "model failed."

## Follow-ups (out of scope; file as beads at Task 3 Step 5 per the verdict)

- Branch (a): wire the winning model as the local nightly authoring default (`providers/llama` model pin) + fuller Track-B confirmation.
- Branch (b): **deterministic advisory pre-selection** — move semver-range advisory matching into recon/`generate.py` (mirror `_resolve_fixed_version`), shrinking the model's job to rationale + PoC; re-measure with this harness.
- Branch (c): the deferred "revisit local authoring when a >7B model fits the 8 GB ceiling" bead, citing this verdict.
- Variance probe (optional): blessed `--seed 42` + temp 0.0 makes trials near-deterministic; a follow-up could sweep temperature to measure authoring *variance* vs a point estimate.

## Completion (2026-06-30)

**Executed; verdict = branch (b), refined — and it overturned the first read.** Track A ran
across the fleet (20 trials each): all four loaded models scored **0.00** live; gemma3-4b
failed to load. Per Task 2 Step 2 that 0.0 skipped Track B (no Docker). **But the adversarial
code-review gate caught that the 0.0 was a measurement artifact, not a capability ceiling.** A
raw-output diagnostic (`runtime/eval/_diag*.ps1`/`_diag.py`) showed every model authors a
*correct* hypothesis (right CVE-2022-3517, sound version-range reasoning); an **offline** probe
through the real `seed_complete` (`runtime/eval/_probe_fix.py`) flips **0/6 → 6/6** under a
3-part field-alignment fix. So: local authoring **is** viable; hb-0vq's premise is disproven;
hb-0vq stays **OPEN** with the alignment fix as its concrete next action, and Track B is to be
run live *after* that fix. Decision artifact:
`docs/superpowers/research/2026-06-30-hb-0vq-local-authoring-verdict.md`. Full suite green
(399 passed, 6 skipped). Commit + `bd` update done at the landing gate. Track-B checkboxes
reflect "resolved by skip (artifactual gate)," not execution.

## Retrospective

_(To be completed after execution — required by the retrospective marker.)_

- **What worked / what surfaced:** did the live matrix reproduce the hb-0vq symptom across the fleet, or did any of the 3 untested models surprise? Was the offline-proven harness faithful to live behavior?
- **Track-B-contingent restructure:** did Track A alone settle the verdict (Track B skipped), validating the adversarial-review cut, or did a model force the Docker path?
- **GPU discipline:** did serialize-and-idle hold under real use; any OOM/contention skips; wall-clock vs estimate.
- **Decision quality:** was the seed_bar/poc_bar choice defensible against the observed rates, or did the data argue different bars?
- **hb-322 impact / framing:** confirm the do-nothing baseline held (Claude carried hb-322) and the verdict cleared the local-path question cleanly.
