---
title: "Experiment 005: Local Pre-commit Linting vs. CI Validation"
date: 2026-03-29
draft: false
type: "docs"
experiment_id: "005"
abstract: "This study evaluates the efficiency of 'shifting left' on code quality by using local pre-commit linting instead of relying solely on CI validation. Results show that local auditing eliminates trivial syntax/style errors and reduces Convergence time by 60%."
hypothesis: "Providing the agent with an automated local lint/format script to run before concluding its work will eliminate 95% of trivial syntax/style errors, resulting in faster Convergence."
methodology:
  model: "Gemini 2.0 Flash"
  temperature: 0.1
  n_trials: 10
  system_prompt: "Comparing 'CI Validation' vs. 'Local Pre-commit Linting' workflows."
---

## 1. Introduction
Waiting for CI to catch trivial errors is inefficient and costly. This experiment tests if empowering agents with local linting tools can significantly improve development speed and quality.

## 2. Methodology
The experimental setup involved introducing deliberate stylistic errors into a project with strict ESLint/Prettier rules. We compared a workflow where the agent waits for CI feedback against a workflow with local pre-commit auditing.

## 3. Results
{{< experiment-metrics id="005" >}}

Local pre-commit auditing is highly effective at catching trivial errors before they pollute documentation or break builds. It reduces Convergence time from an average of 5 steps (including CI wait) to just 2 steps (local fix and verification).

## 4. Discussion & Limitations
While highly effective, the audit scripts must be lightweight to avoid adding overhead. The study demonstrates that shifting left is essential for high-velocity agentic workflows. One limitation is that local environments must perfectly match CI environments for 100% reliability.

## 5. Reproducibility
Verified by Garrett Manley on 2026-03-29.
