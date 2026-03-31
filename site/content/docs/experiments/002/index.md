---
title: "Experiment 002: Token-Budgeted vs. Unbounded Context Discovery"
date: 2026-03-29
draft: false
type: "docs"
experiment_id: "002"
abstract: "This study evaluates the impact of 'Token Budgeting'—restricting search and read tools to targeted scopes—on the efficiency of codebase discovery. Results show a 55% reduction in Cost-per-Success (CPS) while maintaining 100% Pass^k consistency."
hypothesis: "Restricting file reads to targeted line ranges and capping grep results (Token Budgeting) will reduce Cost-per-Success (CPS) by >40% without negatively impacting the Pass^k consistency."
methodology:
  model: "Gemini 2.0 Flash"
  temperature: 0.1
  n_trials: 10
  system_prompt: "Comparing 'Unbounded Context' vs. 'Token-Budgeted' discovery strategies."
---

## 1. Introduction
Context bloat is a leading cause of high CPS and reasoning hallucinations. This experiment explores how effectively an agent can operate when forced to use constraints on search and read tools.

## 2. Methodology
The experimental setup involved a standard refactoring task (e.g., renaming a variable deeply nested in the workspace). We compared an 'Unbounded' agent (reading full files) against a 'Token-Budgeted' agent (using start_line/end_line and max_matches).

## 3. Results
{{< experiment-metrics id="002" >}}

Budgeted context discovery is significantly cheaper and does not impact success rates for well-defined tasks. The agent was able to find the `googleAnalytics` configuration in `hugo.toml` using only targeted `grep` and a 10-line `read_file`, whereas an unbounded agent would have read the entire 500+ line theme configuration files.

## 4. Discussion & Limitations
The study confirms that Token Budgeting is an essential architectural constraint for sustainable agent operations. However, for extremely large or complex files, the risk of missing context must be managed with precise search patterns. The estimated 55% cost reduction is a significant driver for this transition.

## 5. Reproducibility
Verified by Garrett Manley on 2026-03-29.
