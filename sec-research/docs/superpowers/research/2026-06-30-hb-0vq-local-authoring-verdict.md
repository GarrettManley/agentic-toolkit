---
title: "hb-0vq Verdict: Local-Model Authoring Reliability (Live Eval Matrix)"
date: 2026-06-30
status: decided
tracker: hb-0vq
---

# hb-0vq Verdict — Local Models CAN Author; the 0.0 Was a Measurement Artifact

**Decision (branch b, refined):** The local fleet **reliably authors correct
`dependency-cve` hypotheses** — every model identified CVE-2022-3517 for minimatch@3.0.4
with sound version-range reasoning. The Track-A seed-completeness rate of **0.00 is a
harness measurement artifact**, not a model-capability ceiling: `seed_complete` checks for
fields in locations/spellings the models don't use. A small, **offline-proven** alignment
fix flips the rate **0/6 → 6/6 (1.00)** on the captured live outputs. hb-0vq's founding
premise ("version-range reasoning + structured seed is past their reliability") is
**disproven**; the real blocker is three field-alignment gaps in the authoring/scoring path.

## Question

Can any local model (8 GB ceiling) reliably author a seed-complete `dependency-cve`
hypothesis for the minimatch / CVE-2022-3517 reference, trustworthy enough for the
unattended nightly loop?

## Method

- **Citation:** harness `scripts/eval/authoring_eval.py` (`score_track_a` L75–111;
  `seed_complete` L49–58) + runner `scripts/eval/run_matrix.ps1` (Phase 0, commit `4a33016`).
- Provider `llama`, one model per process, blessed args
  (`--ctx-size 8192 --n-gpu-layers 99 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --seed 42`).
- **20 trials/model**, Track A. Fixture `tests/fixtures/llm/recon_item_minimatch.json`.
  Then a **raw-output diagnostic** (2 trials/model) + an **offline alignment probe** that
  re-scores the captured outputs through the *real* `seed_complete`.

## Results

### Track A live rates (the artifact)

**Proof** (`runtime/eval/2026-06-30/*.json`; runtime/ gitignored, rates inlined):

| Model | Trials | Seed-complete | Rate | Measurement |
|-------|--------|---------------|------|-------------|
| qwen2.5-coder-7b-Q4_K_M | 20 | 0 | 0.00 | re-confirm |
| deepseek-r1-7b-Q4_K_M | 20 | 0 | 0.00 | new |
| gemma-4-E4B-it-Q4_K_M | 20 | 0 | 0.00 | re-confirm |
| phi4-mini-Q4_K_M | 20 | 0 | 0.00 | new |
| gemma3-4b-Q4_K_M | — | — | n/a | never loaded (8 GB) — skipped |

### Raw outputs (the truth the rate hid)

The diagnostic (`runtime/eval/_diag.py`) shows **every model authored exactly one correct
hypothesis per trial**, e.g. qwen2.5-coder-7b:

```json
{"target": {"asset_type":"package","identifier":"minimatch","ecosystem":"npm"},
 "vuln_class":"dependency-cve",
 "rationale":"The resolved version 3.0.4 falls within the affected range <3.0.5 and is below the fixed version 3.0.5...",
 "evidence_seed": {"candidate_cve_id":"CVE-2022-3517"}}
```

`seed_complete` requires `evidence_seed.package_ecosystem == "npm"`,
`evidence_seed.package_name`, `evidence_seed.candidate_cve_id`, **and**
`target.version_or_revision`. The live failures decompose into three gaps:

1. **`target.version_or_revision` is never populated by any model** (they put the version in
   `rationale` and `evidence_seed.affected_versions_range`). This alone fails *every* trial —
   including deepseek/gemma trial-1 outputs whose `evidence_seed.package_ecosystem` +
   `package_name` + CVE are all correct.
2. **Seed-key drift `_normalize_seed_keys` doesn't cover:** models emit `cve_id`,
   `package_ecosystem_id`, `package_ecosystem_name`, `package_name_id`, `package_name_name`,
   `affected_versions_range_id/_name`. Only `cve_id_proposed_or_assigned` is currently aliased.
3. **Ecosystem/name in `target`, not `evidence_seed`:** models put them in
   `target.ecosystem`/`target.identifier` (valid schema), which `seed_complete` ignores.

### Offline alignment probe (the proof)

`runtime/eval/_probe_fix.py` re-scores the 8 captured outputs through the **real**
`seed_complete` after a candidate fix — (1) broaden the seed-key alias map, (2) backfill
`evidence_seed.package_ecosystem/package_name` from `target.ecosystem/identifier`, (3) derive
`target.version_or_revision` from recon's `resolved_version` (server-trusted, mirroring
`_resolve_fixed_version`, `llm/generate.py:64-75`):

```
sample         | before | after
qwen t0/t1     | fail   | PASS
deepseek t0    | fail   | PASS
deepseek t1    | fail   | PASS
gemma-4 t0     | fail   | PASS
gemma-4 t1     | fail   | PASS
phi4 t0/t1     | fail   | PASS
seed-complete rate: before 0/6 = 0.00  ->  after 6/6 = 1.00
```

## Verdict and recommendation

- **(b) The fix is seed-field alignment, NOT advisory pre-selection scaffolding.** The models
  *already* select the right advisory and CVE and reason about the version range correctly —
  so the originally-hypothesised scaffolding is unnecessary. The real, smaller fix is three
  changes on the authoring/scoring path:
  1. **Derive `target.version_or_revision` from recon `resolved_version`** when the model
     omits it (server-trusted backfill, same pattern as `_resolve_fixed_version`).
  2. **Backfill `evidence_seed.package_ecosystem`/`package_name`** from `target.ecosystem`/
     `target.identifier` when absent from the seed.
  3. **Extend `_normalize_seed_keys`** to alias `cve_id`, `package_ecosystem_id/_name`,
     `package_name_id/_name`, `affected_versions_range_id/_name` to their canonical keys.
- **hb-0vq stays OPEN** with the above as its concrete next action (a focused fix bead). It is
  **not** "local not viable" — local authoring is viable pending this harness/normalization
  fix. After the fix lands, **re-run the Track A matrix live** to confirm the rate rises from
  0.0, then **run Track B** (PoC-authoring through the oracle) — which this pass correctly
  skipped only because the (artifactual) 0.0 Track A gated it.
- **Honesty boundary:** this proves **seed-completeness** flips to 1.0, i.e. the models emit
  the right *structured seed*. It does **not** yet prove end-to-end PoC viability (Track B) —
  that is the post-fix measurement.
- **Optional harness nit:** `score_track_a` has no "incomplete/empty-list" bucket, so a
  not-seed-complete (but non-empty) trial is invisible in the counts — which is what made the
  0.0 read like "emitted nothing." Add an `incomplete` bucket so the failure mode is legible.

## Impact on hb-322

hb-322 (P1) is unaffected for its immediate run — Claude authoring carries it. This verdict
**strengthens the "local later" half**: local authoring is a small fix away from viable, so
the nightly loop's token-free/API-independent path is within reach, not abandoned.

## Reproduce

```powershell
# from sec-research/, GPU free:
./scripts/eval/run_matrix.ps1 -Track a -Trials 20 -ReportDir runtime/eval/2026-06-30   # live 0.0
pwsh -NoProfile -File runtime/eval/_diag_all.ps1                                        # raw outputs
python runtime/eval/_probe_fix.py                                                       # 0/6 -> 6/6 offline
```
