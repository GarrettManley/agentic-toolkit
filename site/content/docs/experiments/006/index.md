---
title: "Experiment 006: Grammar-Constrained Dependency Scheduling Across Local Models"
date: 2026-06-19
draft: false
type: "docs"
experiment_id: "006"
abstract: "A fair, fully-local benchmark comparing five quantized GGUF models (DeepSeek-R1 7B, Qwen2.5-Coder 7B, Llama 3.1 8B, Gemma-4 E4B, Phi-4-mini) on a structured reasoning task: given a small task-dependency graph with durations and a deadline, emit grammar-constrained JSON giving each task's earliest finish time, the critical-path length, a valid execution order, and whether the deadline is met. Every model is graded by an identical deterministic 4-of-4 oracle against precomputed earliest-finish-time gold, over 60 seeded cases stratified into 4-, 5-, and 6-node difficulty bands, all on a single RTX 4060 via llama-server. A leading ungraded `reasoning` field keeps the chain-of-thought model fair under the grammar constraint. The benchmark isolates dependency-tracking arithmetic from formatting (the grammar guarantees parseable JSON), so oracle failures are reasoning failures. The ranking inverted the obvious expectation: the smallest model, gemma-4-E4B (4B), solved 96.7% of cases [88.6, 99.1] and held 90% even on the hardest 6-node graphs, while the dedicated reasoning model (DeepSeek-R1) and every 7-8B generalist fell below 42% — most of R1's misses being token-budget truncations rather than wrong answers. The discriminating component was exactly the pre-registered one (the per-task `finish_times` map), and the conjunctive oracle exposed a partial-credit illusion: weaker models routinely asserted the correct deadline verdict without computing a correct schedule underneath it."
hypothesis: "Under an identical JSON-schema grammar constraint, local 7-8B models differ measurably in multi-hop dependency arithmetic; the discriminating sub-task is the exact per-task finish_times map (requiring correct multi-predecessor max() propagation), and the inter-model gap widens with graph size."
methodology:
  models: "deepseek-r1-7b, qwen2.5-coder-7b, llama3.1-8b, gemma-4-E4B, phi4-mini (all Q4_K_M)"
  runtime: "llama-server build 9596, one model per process, --flash-attn on, ctx 8192, q8_0 KV cache"
  temperature: 0
  n_cases: 60
  decoding: "grammar-constrained JSON via response_format json_schema; max_tokens 1536; seed 42"
---

## 1. Introduction

Small quantized models are increasingly asked to emit **structured output** — JSON that downstream code consumes directly. Two questions decide whether that is viable on consumer hardware: does grammar-constrained decoding hold the model to a valid schema, and can the model get the *content* right when the content requires multi-step reasoning rather than extraction?

This experiment isolates the second question. We pose a **task-dependency scheduling** problem — a miniature project plan — and require the model to compute, in one grammar-constrained JSON object, each task's earliest finish time, the critical-path length, a valid topological order, and whether a deadline is met. The arithmetic is elementary (integer additions and `max()`), but it must be propagated correctly through a dependency graph: a task starts only after *all* its predecessors finish. This is reasoning, not recall — there is no code to generate, no API to remember, no library idiom that a coding-specialised model would know and a generalist would not.

Because the JSON grammar guarantees that every response parses, an oracle failure is never a formatting failure. It is a **reasoning failure** — the model tracked a dependency wrong, missed a multi-predecessor `max()`, or mis-summed a chain. That is exactly the signal we want to compare across models.

## 2. Methodology

### 2.1 The task

Each case is a small directed acyclic graph of tasks `A..F`, each with an integer duration in `[2, 8]`, plus a set of dependency edges (`U -> V` means *V cannot start until U has finished*) and an integer deadline. The model must return a single JSON object with five fields:

| Field | Type | Graded? |
|---|---|---|
| `reasoning` | string | no — a scratchpad (see §2.4) |
| `topo_order` | array of task labels | yes — must be a valid order for the given edges |
| `finish_times` | object `{label: integer}` | yes — exact earliest finish time per task |
| `critical_path_length` | integer | yes — the maximum finish time |
| `deadline_met` | boolean | yes — `critical_path_length <= deadline` |

The ground truth is a deterministic **earliest-finish-time forward pass**: process tasks in dependency order, set `finish[n] = duration[n] + max(finish[p] for p in predecessors(n))` (tasks with no predecessors start at 0), and take the maximum as the critical-path length.

### 2.2 Case generation (seeded, stratified)

`gen_cases.py` produces 60 cases from a fixed seed (42), hard-stratified into three difficulty bands so the gradient is guaranteed by construction rather than left to sampling luck:

- **Easy** — 20 cases, 4 nodes, edge probability 0.35
- **Medium** — 20 cases, 5 nodes, edge probability 0.45
- **Hard** — 20 cases, 6 nodes, edge probability 0.55

Graphs are acyclic by construction (forward-only edges over a random linear order), with in-degree capped at 2 to keep the arithmetic hand-traceable. Deadlines are balanced to ~50% feasible / ~50% infeasible, and at least two cases per band are forced to `deadline == critical_path_length` exactly, so the discriminating "meets the deadline *exactly*" comparison is always exercised. `verify_gold.py` re-derives the gold independently from the published cases so the answers need not be trusted.

### 2.3 The oracle

`grade()` is fully deterministic — no LLM, no floats. A case passes only if **all four** graded components are correct:

1. `deadline_met` matches (a boolean — resistant to lucky guessing only because it is conjoined with the rest),
2. `critical_path_length` matches (integer-coerced),
3. `finish_times` has *exactly* the right key set and every value is correct,
4. `topo_order` is a valid ordering — checked **against the edge list**, never against a single canonical order, so all valid orderings are accepted.

The `finish_times` map is the hard component: it requires correct multi-predecessor `max()` propagation through the whole graph, and it is where stronger models still slip on larger graphs. The 4-of-4 conjunction is the calibration mechanism — easy components (`deadline_met`, `critical_path_length`) set a reachable floor while `finish_times` creates the ceiling.

### 2.4 Fairness to the reasoning model

A JSON-schema grammar constrains output from the very first token, which would normally prevent a chain-of-thought model (DeepSeek-R1) from emitting its usual `<think>` block. To keep the comparison fair, the schema places an ungraded `reasoning` string **first** in property order; llama-server's grammar preserves that order, so every model — the reasoner especially — works the problem out in `reasoning` before committing to the answer fields. The reasoner's verbosity is then reported honestly as **tokens-per-success**, not punished as failure. `max_tokens` is 1536 (a deliberate increase after a probe showed R1 truncating at 400), identical for every model.

### 2.5 Models and runtime

Five Q4_K_M GGUFs, each run one-process-at-a-time through **llama-server** (build 9596) under the 8 GB VRAM ceiling, with the workspace's blessed arguments (`--n-gpu-layers 99 --flash-attn on --ctx-size 8192 --cache-type-k q8_0 --cache-type-v q8_0 --seed 42`), greedy decoding (`temperature 0`) for bit-reproducibility on the same GPU. The slate spans five vendors — DeepSeek (reasoning), Qwen (coding), Meta, Google, and Microsoft. (The originally-planned `gemma3-4b` GGUF is incompatible with build 9596 — a missing hyperparameter key — so the working `gemma-4-E4B` was substituted and `phi4-mini` added as the small-model representative.)

Per model we record Pass^k with a Wilson 95% confidence interval, decode throughput (tokens/second), tokens-per-success, per-band pass rates, per-component pass rates, and mean reasoning length.

## 3. Results

{{< experiment-model-chart >}}

{{< experiment-model-table >}}

The table and chart above render the live numbers from this experiment's `data.json`. Three findings stand out.

### 3.1 The ranking inverted the obvious expectation

The smallest model on the slate won, decisively. **gemma-4-E4B** (a ~4 B-parameter model) passed **96.7%** of cases (58/60, Wilson 95% CI [88.6, 99.1]). **No other model cleared 42%.** The dedicated reasoning model, DeepSeek-R1 7B, came second at 41.7%; the dedicated coding model, Qwen2.5-Coder 7B, third at 33.3%; Phi-4-mini fourth at 25.0%; and Llama 3.1 8B last at 21.7%. Neither parameter count nor task-specialisation predicted the outcome — a 4 B generalist beat a 7 B reasoning specialist and a 7 B coding specialist on the same multi-hop arithmetic by **more than 55 percentage points**.

### 3.2 R1's headline number is mostly a token-budget artifact, not a capability ceiling

DeepSeek-R1 hit the 1536-token cap **before closing its JSON on 29 of 60 cases** (`schema_fail_count = 29`). Under grammar-constrained decoding a schema failure can *only* be a truncation — the grammar guarantees validity for any output that finishes — so R1 spent its budget reasoning and ran out before committing the answer. On the 31 cases where it *did* emit valid JSON within budget, it was correct on 25 — **≈81%**, second only to gemma. Its tokens-per-success (3,113) is **5.4× Qwen's** (577), the cost of that verbosity made explicit. The "fairness" accommodation — an ungraded reasoning-first field plus a raised 1536-token cap, identical for every model — was meant to *protect* the reasoner; instead it surfaced a real deployment hazard (see §4.2). By contrast Llama 3.1's low score is *not* primarily a truncation story: only 10 of its misses were truncations, and even on its 50 valid outputs just 26% were correct — it mostly computed the schedule wrong.

### 3.3 Every model collapses on the hard band — except gemma

The pre-registered prediction that the gap widens with graph size is confirmed emphatically. Across the 6-node "hard" band, pass rates crater: R1 0.60 → 0.55 → **0.10**, Qwen 0.60 → 0.25 → **0.15**, Llama **0.20 → 0.40 → 0.05**, Phi-4-mini 0.30 → 0.30 → **0.15**. gemma alone holds: **1.00 / 1.00 / 0.90**. The discriminating sub-task is exactly the one named in the hypothesis — the per-task `finish_times` map. The component breakdown makes this concrete: gemma's four graded components all pass at **0.967 in lockstep** (when it is right, it is right on the whole object), whereas the weaker models post *scattered* component rates — Qwen, for instance, gets `deadline_met` right 80% of the time but `finish_times` only 33%. That gap is the **partial-credit illusion** the 4-of-4 oracle was built to expose: a model can assert the correct yes/no deadline verdict by heuristic while having no correct schedule underneath it. Only the conjunction of all four components separates real dependency-tracking from a lucky boolean.

## 4. Discussion & Limitations

### 4.1 Capability did not track size or specialisation

The headline is a caution against picking a local model by reputation. The slate was chosen so that the "expected" winners were obvious — a reasoning-tuned model and a code-tuned model, both 7 B, against smaller generalists — and both expected winners lost to a 4 B model that is marketed for neither reasoning nor code. Coding specialisation did not transfer to dependency arithmetic, and an explicit chain-of-thought did not beat a model that simply got the arithmetic right in fewer tokens. For a structured multi-hop task on an 8 GB card, the only reliable selection method is to **measure on the actual task** — gemma-4-E4B is the deployment choice here on all three axes at once: highest accuracy (96.7%), no collapse at scale (90% on the hard band), and a healthy 52 tok/s. (It is the same model this lab uses as the [Aether intent classifier](../007/) — a consistent picture of a small model that punches well above its parameter count on structured tasks.)

### 4.2 The reasoning model's real lesson is about output budgets

The most transferable finding is not "R1 is weak" — on completed cases it was the second-strongest model — but that **a reasoning model is fragile under a fixed output budget**. Given an equal, generous 1536-token cap, R1 truncated on nearly half the cases because it consumed the budget on its chain-of-thought and never reached the answer. Raising the cap or letting the reasoner stream freely would recover that capability, but in a real structured-output pipeline the budget is fixed by latency and the schema is consumed by code: under those constraints the reasoning model is *less* reliable than a terse generalist, not more. That is a deployment property worth knowing before reaching for a CoT model to emit JSON on a deadline.

### 4.3 Why the conjunctive oracle matters

Reporting any single component would have produced a flattering, wrong leaderboard — most models answer `deadline_met` correctly ~70-80% of the time. Only requiring all four components together (`deadline_met`, `critical_path_length`, the exact `finish_times` map, and a valid `topo_order`) separates models that *compute the schedule* from models that *guess the verdict*. The component-rate spread in §3.3 is the evidence: a model whose `deadline_met` rate far exceeds its `finish_times` rate is pattern-matching the easy boolean, not reasoning about the graph.

### 4.4 Limitations

1. **Quantization.** All models are Q4_K_M; a higher-precision quant or the same family at a different size would shift the absolute numbers. The comparison is "what fits and runs fast on an 8 GB card," not "the model's best possible score."
2. **Single task family.** Dependency scheduling rewards careful state-tracking arithmetic; it is not a proxy for code generation, retrieval, or open-ended reasoning. A model that trails here may lead on other axes.
3. **Greedy decoding, single sample.** One temperature-0 trial per case makes results reproducible but does not estimate within-model variance from sampling; Pass^k variance is captured only across the 60 cases (via the Wilson interval).
4. **Grammar overhead unmeasured.** The grammar constraint guarantees valid JSON but may itself bias decoding; this experiment does not isolate constrained-vs-free decoding for the same model.
5. **R1's score understates its capability.** Because R1's failures are dominated by token-budget truncation (§3.2), its 41.7% is a *budget-constrained* result, not a measure of its scheduling ability with unbounded output. It is reported as-is because every model ran under the identical 1536-token budget — the comparison is fair, but R1's number should be read as "reliability under a fixed budget," not "peak capability."
6. **Transient GPU contention on one model.** Llama 3.1 ran while the GPU was shared with an unrelated foreground application, inflating its *wall-clock* time roughly 6.6× (≈2400 s vs ≈360 s of actual generation). Correctness is unaffected — decoding is seed-deterministic, so the same tokens are produced regardless of scheduling — and the reported throughput (35.4 tok/s) comes from llama-server's generation timer, which measures active compute only, not wall-clock. No graded metric depends on wall-clock time.

## 5. Reproducibility

Everything needed to reproduce this benchmark is published alongside this page:

- `gen_cases.py` — regenerates the 60 cases and the gold from seed 42.
- `verify_gold.py` — independently re-derives the earliest-finish-time gold and asserts it matches.
- `eval.py` — runs the full slate against llama-server and writes `data.json`.
- `cases.json`, `gold.json`, `cases_meta.json`, `results_full.json` — the committed inputs and full per-band / per-component results.

To reproduce: `python gen_cases.py && python verify_gold.py && python eval.py`. Greedy decoding (`temperature 0`) makes the run bit-reproducible on the same GPU and llama-server build (9596). Conducted by Garrett Manley on 2026-06-19.
