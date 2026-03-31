---
title: "Experiment 003: Single-Shot vs. Mandatory Verification Step"
date: 2026-03-29
draft: false
type: "docs"
experiment_id: "003"
abstract: "This study measures the impact of forced self-reflection and tool-based verification on agent reliability. Results indicate that mandatory execution of verification commands increases Pass^k consistency from 65% to 98%, despite a slight increase in Convergence steps and cost."
hypothesis: "Requiring the agent to successfully execute a verification command (e.g., running a script or test) before marking a task complete will increase Pass^k by at least 30%."
methodology:
  model: "Gemini 2.0 Flash"
  temperature: 0.1
  n_trials: 10
  system_prompt: "Comparing 'Single-Shot' generation vs. 'Mandatory Verification' step."
---

## 1. Introduction
'Single-shot' code generation often fails due to minor syntax errors or incorrect assumptions that aren't caught until human review or CI. This experiment tests if local self-healing via mandatory verification can close this gap.

## 2. Methodology
The experimental setup involved a feature implementation task. We compared 'Single-shot' performance (agent finishes when code is written) against a 'Mandatory Verification' constraint (agent MUST run a verification script and fix errors).

## 3. Results
{{< experiment-metrics id="003" >}}

Mandatory verification is the single most important factor in reaching high-reliability (Pass^k) agentic performance. While it increases the turn count (Convergence), it ensures that the agent catches its own mistakes. The cost increase of ~$0.02 is negligible compared to the gain in reliability.

## 4. Discussion & Limitations
The study demonstrates that verification prevents failures where paths or dependencies are incorrectly assumed. While effective, the verification scripts must be robust and provide clear error signals for the agent to action correctly.

## 5. Reproducibility
Verified by Garrett Manley on 2026-03-29.
