---
title: "Experiment 005: Local Pre-commit Linting vs. CI Validation"
date: 2026-03-29
draft: false
type: "docs"
experiment_id: "005"
abstract: "This study evaluates the efficiency of 'Shifting Left' on code quality by using local pre-commit auditing instead of relying solely on remote CI validation. Results from 10 comparative trials demonstrate that local linting and formatting eliminate 95% of trivial syntax/style errors and reduce average Convergence time by 60% (from 5 turns to 2). By empowering agents with local CLI audit tools, the project minimizes the 'CI Lag'—the non-productive wait time for remote validation—and significantly lowers the Cost-per-Success (CPS) from $0.15 to $0.05. These findings support a mandatory 'Local Pre-commit Audit' step for all autonomous agent workflows to ensure high-velocity, high-quality development."
hypothesis: "Providing the agent with an automated local lint/format script to run before concluding its work will eliminate >90% of trivial syntax/style errors, resulting in faster Convergence."
methodology:
  model: "Gemini 2.0 Flash"
  temperature: 0.1
  n_trials: 10
  system_prompt: "Comparing 'CI-Only' validation (agent finishes and waits for remote CI feedback) vs. 'Local Pre-commit' auditing (agent MUST run `npm run lint --fix` and `npm run format` locally before finishing)."
---

## 1. Introduction
Waiting for a CI/CD pipeline to catch a missing semicolon or a misaligned brace is one of the most inefficient patterns in autonomous software engineering. These trivial errors, while easily fixed, often result in a 'Failed' status in CI, requiring a full context reload and a new agentic session to resolve. This experiment explores 'Shifting Left'—the practice of moving validation as close to the point of authorship as possible. By integrating local linting (ESLint) and formatting (Prettier) into the agent's core loop, we aim to prove that local auditing is a prerequisite for high-velocity agentic workflows.

## 2. Methodology
The study used a 10-trial comparison of two distinct validation workflows.

### 2.1 Experimental Workflows
- **CI-Only Workflow:** The agent completed its task and triggered a simulated remote CI pipeline (a 5-minute 'wait' state followed by failure/success feedback).
- **Local Pre-commit Workflow:** The agent was mandated to execute local audit commands (`eslint --fix` and `prettier --write`) before calling `complete_task`.

### 2.2 Task Definition
The agent was tasked with introducing a new function into a project with strict stylistic rules. We deliberately injected 'Trivial Noise'—e.g., using double quotes instead of single quotes, or adding excessive whitespace—to test the audit tools' effectiveness.

### 2.3 Hardware and Software Stack
- **Audit Tools:** ESLint v9.0, Prettier v3.2.
- **Environment:** Local Node.js workspace.
- **Model:** Gemini 2.0 Flash (Cloud Synthesis).

### 2.4 Metrics
- **Pass^k Consistency:** Percentage of trials that passed CI on the *first* attempt.
- **Convergence Time:** Total turns (agent interactions) required to reach a stable, CI-passing state.
- **Cost-per-Success (CPS):** Total token cost of all turns divided by successful trials.

## 3. Results
{{< experiment-metrics id="005" >}}

The results establish Local Pre-commit Auditing as a massive efficiency driver.
- **Pass^k Consistency:** Improved from 80% (CI-Only) to 100% (Local).
- **Convergence Steps:** Reduced from an average of 5.0 turns to just 2.0.
- **Cost-per-Success (CPS):** Decreased by 66% (from $0.15 to $0.05).

In the 'CI-Only' workflow, the agent often had to 'wake up' for a second session to fix a single linting error caught by CI, doubling its cost and quadrupling the real-world time to completion. In the 'Local Pre-commit' workflow, the agent used its first turn to write code and its second turn to run the audit and confirm success. The `eslint --fix` command automatically resolved 95% of stylistic issues without further agent reasoning, essentially providing 'Free Success' for stylistic errors.

## 4. Discussion & Limitations
### 4.1 Theoretical Insights: Shifting Left for Agents
This study confirms that 'Shifting Left' is even more critical for agents than for humans. While a human might ignore a linting error due to fatigue, an agent can be architecturally constrained to never commit code that hasn't passed a local audit. This 'Automated Quality Gate' ensures that only high-signal code reaches the repository, protecting the codebase's integrity and reducing the load on CI infrastructure.

### 4.2 Limitations
1. **Rule Parity:** If local linting rules do not exactly match CI rules, 'Local Success' may still lead to 'CI Failure'.
2. **Computational Overhead:** Running heavy linting or formatting on every turn can add significant local CPU latency, which must be balanced against the time saved from avoided CI failures.
3. **Complex Errors:** Audit tools can fix style, but they rarely fix logical errors. Local auditing is a complement to, not a replacement for, **Mandatory Verification** (Exp 003).

### 4.3 Integration with Hybrid Context Synthesis
The Local Pre-commit Audit is the first stage of the 'Validation' phase in the **Hybrid Context Synthesis** protocol (Exp 001). It ensures that the 'Synthesis' produced by the cloud model is idiomatically consistent with the 'Local Audit' environment before final verification.

## 5. Reproducibility
The experiment used the `precommit-auditor` v1.1.0 plugin. Raw audit logs and CI simulation reports are archived in `site/data/experiments/005_raw.json`. Verified by Garrett Manley on 2026-03-29.
