# Phase 3: Learning & Maintenance Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish a non-interactive, scheduled service (The Nightly Steward) that performs workspace audits, drift checks, and model research to ensure the "Living Truth-Base" remains accurate and leading-edge.

**Architecture:** A PowerShell-driven orchestration loop that triggers the Local Orchestration Layer (Phase 2) to perform multi-round tasks and outputs results to a "Morning Briefing" document.

**Tech Stack:**
- **Orchestration**: PowerShell 7
- **Reasoning**: Qwen-Orchestrator (Tooling) + DeepSeek-R1 (Reasoning)
- **Reporting**: Markdown (Morning Briefing)
- **Scheduling**: Windows Task Scheduler

---

### Task 1: The Morning Briefing Foundation

**Files:**
- Create: `.ai/templates/morning-briefing.md`
- Create: `.ai/context/maintenance/audit-history.md`

- [ ] **Step 1: Create the Briefing Template**
Define the structure for reporting verified changes, identified drift, and pending decisions.

- [ ] **Step 2: Initialize Audit History**
Create a machine-readable log to track the performance and pass-rate of nightly tasks.

---

### Task 2: The Nightly Steward (Core Script)

**Files:**
- Create: `.ai/scripts/steward.ps1`

- [ ] **Step 1: Implement "Drift Check" Logic**
Write a loop that reads every `.ai/context/*.md`, extracts the `verification_cmd`, and executes it.

- [ ] **Step 2: Implement "Consensus Capture"**
If a command fails, the script must flag the drift and add it to the Morning Briefing instead of failing the entire run.

- [ ] **Step 3: Integrate with Local Gateway**
Ensure the steward uses the Port 8000 bridge for any tasks requiring tool-calling.

---

### Task 3: Horizon Scanning Routine

**Files:**
- Modify: `.ai/skills/horizon-scanning/SKILL.md`
- Create: `.ai/scripts/scan-horizon.py`

- [ ] **Step 1: Automate Research**
Create a Python script that uses `google_web_search` to find new 2026 models and MCP servers.

- [ ] **Step 2: Update Model Tiers**
If a "Superior Tier" is found, the steward proposes an update to ADR 002.

---

### Task 4: CI/CD for Knowledge (The Safety Hook)

**Files:**
- Create: `.git/hooks/pre-commit` (Simulated for Workspace Repo)

- [ ] **Step 1: Implement Truth-Validator Hook**
A script that prevents committing code if the `.ai/` context has not been updated within the same session.

---

### Task 5: Final Loop Verification

- [ ] **Step 1: Run Manual Steward Audit**
Execute the full steward script and verify the generated Morning Briefing.

- [ ] **Step 2: Commit Phase 3 Completion**
```bash
git add .
git commit -m "feat: complete phase 3 learning and maintenance loop"
```
