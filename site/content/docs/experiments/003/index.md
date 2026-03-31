---
title: "Experiment 003: Single-Shot vs. Mandatory Verification Step"
date: 2026-03-29
draft: false
type: "docs"
experiment_id: "003"
abstract: "This study explores the impact of a mandatory, tool-enforced verification step on the reliability of autonomous software engineering agents. Using 100 trials, we compared a 'Single-Shot' generation strategy with a 'Mandatory Verification' protocol. Results demonstrate that forcing the agent to execute a local validation command (e.g., a linter, test, or build script) increases Pass^k consistency from 65% to 98%. Although this protocol increases the turn count (Convergence) from 1 to 3 steps and slightly raises the average Cost-per-Success (CPS) to $0.07, the 33% gain in reliability is a foundational requirement for production-grade agentic authorship. These findings support the adoption of 'Local Verification' as a non-negotiable step in the agentic development lifecycle."
hypothesis: "Requiring the agent to successfully execute a verification command (e.g., running a script or test) before marking a task complete will increase Pass^k consistency by >30%."
methodology:
  model: "Gemini 2.0 Flash"
  temperature: 0.1
  n_trials: 100
  system_prompt: "Comparing 'Single-Shot' generation (finishing when code is written) vs. 'Mandatory Verification' (finishing only after a successful `run_shell_command` validation)."
---

## 1. Introduction
The most common point of failure for autonomous agents is 'Surgical Success with Integrated Failure'—where a local change is syntactically correct but breaks the broader system due to pathing, dependency, or runtime errors. Traditional 'Single-Shot' generation strategies rely on the agent's internal world model to predict these outcomes, which frequently results in hallucinations. This experiment introduces **Mandatory Verification** as a corrective feedback loop. By requiring agents to run actual code in a local shell before concluding their mission, we aim to close the reliability gap.

## 2. Methodology
The experiment evaluated 100 trials comparing two distinct workflows for a feature implementation task.

### 2.1 Experimental Frameworks
- **Single-Shot Workflow:** The agent was permitted to issue a `complete_task` call immediately after performing a file edit. Its success was judged post-hoc by a human or a CI system.
- **Mandatory Verification Workflow:** The agent was strictly instructed that it could ONLY call `complete_task` after successfully running a project-relevant verification script (e.g., `npm run test`, `go test ./...`, or a custom `grep` check) that produced a non-zero exit code.

### 2.2 Task and Environment
Each trial involved a cross-file refactor in a multi-file Node.js project. For instance, renaming a shared utility function across multiple consumers.
- **Hardware:** Standard CPU-based local environment with CLI tool access.
- **Model:** Gemini 2.0 Flash (Cloud Synthesis) with tool calling enabled.

### 2.3 Success and Metrics
- **Pass^k Consistency:** The percentage of trials where the final codebase was functionally correct and passed all CI checks.
- **Convergence:** The number of agent turns (messages) required to reach completion.
- **Cost:** Total token cost of the entire multi-turn interaction.

## 3. Results
{{< experiment-metrics id="003" >}}

The empirical data establishes Mandatory Verification as the single most critical factor in achieving high-reliability (Pass^k) performance.
- **Pass^k Consistency:** Improved from 65% in the Single-Shot baseline to 98%.
- **Convergence Steps:** Increased from 1.0 (by definition) to 3.0.
- **Cost-per-Success (CPS):** Rose slightly from $0.05 to $0.07.

The 25% cost increase is negligible compared to the 33% absolute gain in reliability. In the Single-Shot trials, failures were typically caused by small syntax errors (e.g., missing imports) or incorrect relative paths. In the Mandatory Verification trials, the agent encountered these same errors but used the shell output to self-correct in its second or third turn, reaching a 98% success rate.

## 4. Discussion & Limitations
### 4.1 The Self-Healing Loop
Mandatory Verification transforms the agent from a 'Writer' into a 'Tester-Refiner'. By grounding the agent in the reality of the local shell, we bypass the limitations of its internal 'world-model' for predicting execution results. This study demonstrates that 'Grounding via Execution' is superior to 'Grounding via Description' for software tasks.

### 4.2 Limitations
1. **Verification Script Quality:** The reliability of this method is entirely dependent on the quality of the verification scripts. If a script produces a 'False Success', the agent will conclude its mission with a broken implementation.
2. **Environment Drift:** If the local verification environment differs significantly from the production/CI environment, agents may achieve 'Local Success' that fails in CI.
3. **Infinite Loops:** If an agent cannot diagnose a persistent shell failure, it may exhaust its turn limit without converging, increasing cost without achieving success.

### 4.3 Integration with Hybrid Context Synthesis
The Mandatory Verification step is the final 'Validation' phase in the **Hybrid Context Synthesis** protocol (Exp 001). It ensures that the high-level synthesis is correctly applied to the local filesystem, closing the loop between cloud reasoning and local execution.

## 5. Reproducibility
All 100 trials were logged using the `superpowers-verify` v0.5.2 tool. Raw logs and verification scripts are available in `site/data/experiments/003_raw.json`. Verified by Garrett Manley on 2026-03-29.
