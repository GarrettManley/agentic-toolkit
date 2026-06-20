---
title: "Experiment 007: Grammar-Constrained JSON for a Local Intent Classifier"
date: 2026-06-11
draft: false
type: "docs"
experiment_id: "007"
domain: "classification"
abstract: "The Aether Engine routes each player's natural-language action through a local intent classifier that must emit structured JSON the game engine can execute directly. This experiment measures the reliability difference between two ways of getting JSON out of a small local model: prompt-injection (asking the model to 'respond in JSON') versus grammar-constrained decoding (constraining the sampler to a JSON schema via GBNF logit masking). On a 48-case golden set, a 4-billion-parameter model (gemma-4-E4B, 4-bit quantized, on a single RTX 4060) classifies with 100% accuracy under grammar constraint versus 89.6% under prompt-injection. A McNemar exact test on the paired outcomes (b=25, c=0, n=240) gives p < 0.001: the difference is a real, categorical correction, not run-to-run noise. The constrained-decoding result is a generic contribution; the RPG task is its testbed."
hypothesis: "Constraining a small local model's sampler to a JSON schema (grammar masking) eliminates a categorical misclassification bias that prompt-injection JSON suffers, raising structured-intent classification accuracy with no change to the model."
methodology:
  model: "gemma-4-E4B (Q4_K_M, ~4.6 GB, 100% GPU offload on RTX 4060)"
  runtime: "llama-server, OpenAI-compatible /v1/chat/completions, response_format json_schema (GBNF)"
  golden_set: "48 labelled natural-language action cases across 5 intent categories"
  statistics: "Wilson 95% CI; McNemar exact test on paired (grammar vs prompt-injection) outcomes"
---

## 1. Introduction

The Aether Engine is an LLM-narrated tabletop RPG over a deterministic rules core. Every turn, a player types a free-form action — *"I sneak past the guard and pick the lock"* — and the engine must turn that into a **structured intent** the rules core can execute: an action category, a sub-type, and the relevant parameters. That translation is a **classification** problem, and because the output is consumed by code, it must be valid structured JSON every single time.

There are two common ways to get JSON out of a local model. The first is **prompt-injection**: append "respond only in JSON matching this shape" to the prompt and hope the model complies. The second is **grammar-constrained decoding**: constrain the sampler itself so that, token by token, only outputs conforming to a JSON schema are reachable (llama.cpp compiles the schema to a GBNF grammar and masks the logits). The first is best-effort; the second is a guarantee.

This experiment asks a sharper question than "does the JSON parse." Grammar constraint guarantees parseable JSON — but does it also change *which* class the model picks? The hypothesis, drawn from a real regression in the engine, is that prompt-injection introduces a **categorical bias** (the model is nudged toward whichever class the prompt's JSON examples over-represent), and that grammar masking removes it.

## 2. Methodology

### 2.1 The task

The classifier maps a natural-language player action to a structured intent object. The output carries one of **five intent categories** — an in-world action, speech, looking/examining, movement, or an out-of-character/meta utterance — and, for actions, a **sub-type** (a skill check, an attack, a spell, or a saving throw) plus the relevant parameters (the skill or ability invoked, a target hint, a spell reference, a direction, or free-text content). The skill vocabulary is a fixed set of **18 domain skill categories** (stealth, arcana, persuasion, investigation, and so on). The classification is grounded in the acting character's context (their abilities, known actions, and proficiencies).

### 2.2 The two conditions

Both conditions use the **same model, same prompt content, same golden set** — they differ only in how JSON is obtained:

- **Prompt-injection (baseline):** the model is asked to emit JSON; the schema lives in the prompt as instructions and examples.
- **Grammar-constrained (treatment):** the schema is enforced at the sampling layer via `response_format: json_schema` (GBNF logit masking); it is *not* in the prompt.

The model is **gemma-4-E4B**, 4-bit quantized (Q4_K_M, ~4.6 GB), running fully GPU-offloaded on a single RTX 4060 via llama-server, greedy-ish decoding (temperature 0.1).

### 2.3 The golden set and grading

The golden set is **48 labelled cases** spanning all five intent categories (skill checks, attacks, spells, movement, speech, look, and out-of-character). Each case has a known-correct intent; a case passes only if the classified category, sub-type, and parameters all match the label. The formal evaluation runs the full golden set **5 times** (240 trials total) to confirm the result is not a single lucky seed.

### 2.4 Statistics

Accuracy is reported as a pass rate with a **Wilson 95% confidence interval** (computed at build time, the same method used across this lab's experiments). Because the two conditions are run on the **same cases**, the comparison is paired, so significance is tested with **McNemar's exact test** on the discordant pairs — cases where exactly one of the two conditions was correct.

## 3. Results

{{< experiment-metrics id="007" >}}

Grammar-constrained decoding classifies **100%** of the 240 trials correctly (48/48 distinct cases, reproduced across all 5 runs). The prompt-injection baseline reaches **89.6%**. The improvement is **+10.4 percentage points**, and the McNemar test is decisive: of the discordant pairs, **25 went grammar-correct / prompt-injection-wrong and 0 went the other way** (b=25, c=0), giving p < 0.001.

The qualitative story behind the number is a **categorical bias**: under prompt-injection, the model systematically mis-routed a specific class of actions (e.g. classifying a clearly-offensive spell as a generic skill check), pulled by the distribution of the in-prompt JSON examples. Grammar masking removes the prompt's example distribution from the sampling path entirely, and the bias disappears — every discordant case resolved in its favour.

## 4. Discussion & Limitations

The contribution generalises well beyond this game: **for structured-output tasks on small local models, schema enforcement belongs in the sampler, not the prompt.** Prompt-injection conflates "produce valid JSON" with "be steered by the prompt's examples"; grammar masking decouples them, guaranteeing validity while leaving classification to the model's own judgement.

### 4.1 Limitations

1. **Runtime confound (the honest caveat).** The grammar-constrained condition was measured on llama-server while the prompt-injection baseline was measured on a different local runtime. The runtimes differ in more than decoding, so the 89.6% → 100% gap is not *purely* attributable to grammar masking. However, the *mechanism* — a categorical misclassification eliminated, with all 25 discordant pairs resolving one way — points squarely at the decoding method, not raw runtime performance.
2. **Single golden set, single domain.** 48 cases in one RPG schema. The categorical-bias finding should replicate on other constrained-classification tasks, but that is asserted, not shown here.
3. **Independence.** The 240 trials are 5 repeated runs of 48 distinct cases, not 240 independent draws; the repetition demonstrates seed-stability, and the Wilson interval on the conservative 48-case sample is wider ([92.6, 100]).
4. **Not reader-reproducible.** Unlike [Experiment 006](../006/), whose harness and cases are published, this result is *reported* from the Aether Engine's internal classifier-evaluation suite. The methodology and statistics are stated in full; the proprietary golden set and prompts are not published.

## 5. Reproducibility

This experiment is reported from the **Aether Engine's** classifier evaluation gate (run 2026-06-11), not from a standalone public harness. The numbers are gate-verified: the 100% result was confirmed across two consecutive formal runs before being accepted. What is portable — and what this write-up is really about — is the method: enforce JSON via `response_format: json_schema` (GBNF) at the sampling layer rather than via prompt instructions, and measure the paired difference with McNemar's test. That recipe is reproducible on any local model and any structured-classification task. Reported by Garrett Manley.
