---
title: "Experiment 002: Token-Budgeted vs. Unbounded Context Discovery"
date: 2026-03-29
draft: false
type: "docs"
experiment_id: "002"
abstract: "This study evaluates the impact of 'Token Budgeting'—the enforcement of architectural constraints on search and read tools—on the efficiency of codebase discovery in autonomous agents. In a 10-trial comparative analysis, we show that restricting file reads to targeted line ranges and capping grep search results leads to a 55% reduction in Cost-per-Success (CPS) while maintaining 100% Pass^k consistency. The research demonstrates that 'Unbounded Context' approaches often lead to redundant token consumption and increased reasoning latency. By implementing a 'Budgeted Discovery' protocol, agents can effectively navigate large workspaces using surgical context acquisition, establishing a scalable foundation for cost-effective agentic engineering."
hypothesis: "Restricting file reads to targeted line ranges and capping grep results (Token Budgeting) will reduce Cost-per-Success (CPS) by >40% without negatively impacting the Pass^k consistency."
methodology:
  model: "Gemini 2.0 Flash"
  temperature: 0.1
  n_trials: 10
  system_prompt: "Operate as a 'Budget-Aware Engineer'. Always use `start_line` and `end_line` for `read_file`. Limit `grep_search` to a maximum of 50 results. Prioritize surgical discovery over exhaustive file reading."
---

## 1. Introduction
Context bloat is the 'silent killer' of agentic efficiency. When an agent reads entire 1,000-line files to find a 5-line configuration block, it consumes unnecessary tokens, increases reasoning latency, and risk 'lost in the middle' hallucinations where the primary target is buried under irrelevant metadata. This experiment explores **Token Budgeting**—an intentional architectural constraint—as a mitigation strategy. By forcing agents to use high-precision tools like targeted `grep` and ranged `read_file`, we aim to prove that 'Surgical Discovery' is not only cheaper but equally reliable for standard engineering tasks.

## 2. Methodology
The experiment compared two agentic strategies across 10 trials within a complex repository (~500 files).

### 2.1 Experimental Strategies
- **Unbounded Strategy:** The agent was permitted to use `read_file` without line range constraints and `grep_search` without result caps. This represents the default 'naïve' agent behavior.
- **Token-Budgeted Strategy:** The agent was strictly instructed (via system prompt) to use `start_line` and `end_line` for all file reads and to cap `grep_search` results at 50.

### 2.2 Task Definition
Each trial required the agent to find and modify a deeply nested configuration variable (e.g., a specific analytics ID in a large `hugo.toml` file or a version constant in a package dependency file). This task was chosen to emphasize the difference between reading a whole file and searching for a specific key.

### 2.3 Hardware and Configuration
- **Model:** Gemini 2.0 Flash (Cloud-based Synthesis).
- **Environment:** Local VS Code-like workspace with integrated CLI tools.
- **Constraints:** A maximum turn count of 5 was enforced to ensure the agents reached convergence efficiently.

## 3. Results
{{< experiment-metrics id="002" >}}

The results confirm that Token Budgeting is an essential architectural constraint.
- **Cost-per-Success (CPS):** Reduced from a baseline of $0.10 to $0.045 (a 55% reduction).
- **Pass^k Consistency:** Remained at 100% for both strategies.
- **Token Consumption:** The Budgeted agent used an average of 4,200 tokens per trial, compared to ~9,500 for the Unbounded agent.

A specific example illustrating the difference occurred during the discovery of the `googleAnalytics` configuration in the project's root `hugo.toml`. The Unbounded agent read the entire 600-line file (approx. 2,400 tokens). The Budgeted agent used `grep_search` to find the line number (15 tokens) and then a 10-line `read_file` (approx. 40 tokens) to confirm the surrounding context.

## 4. Discussion & Limitations
### 4.1 Theoretical Insights
Token Budgeting shifts the cognitive load from 'Brute Force Reading' to 'Precise Locating'. By requiring the agent to be intentional about what it reads, the architecture encourages the use of the file system's structure and existing search indices. This study confirms that for well-defined engineering tasks, full file context is rarely necessary and often counter-productive.

### 4.2 Limitations
1. **False Negatives:** In extremely large repositories where symbols are duplicated, a capped `grep_search` (e.g., max 50) might miss the correct target if it appears late in the file system walk.
2. **Heuristic Failure:** For tasks requiring holistic file understanding (e.g., refactoring a complex class structure), Token Budgeting may require more turns to build a mental map, potentially increasing the Turn-count even if the total token count is lower.

### 4.3 Hybrid Context Synthesis
The findings here integrate directly with **Hybrid Context Synthesis** (Exp 001). The 'Local Audit' phase is most effective when it is Token-Budgeted, ensuring that the filtered context sent to the 'Cloud Synthesis' phase is pure, high-signal, and cost-optimized.

## 5. Reproducibility
The experiment utilized the `context-limiter` v0.9.1 plugin. Trial data and raw token logs are available in `site/data/experiments/002_data.json`. Verified by Garrett Manley on 2026-03-29.
