# Learning and Maintenance Loop Plan

**Tracker:** hb-doc.2 · **Status:** Completed (historical, 2026-03) · **Phase:** 3

> For agentic workers: use `superpowers:subagent-driven-development` (preferred) or `superpowers:executing-plans` to run this plan task-by-task.

## Goal and value

Establish a non-interactive, scheduled service (the Nightly Steward) that audits the workspace, checks for drift, and researches new models, keeping the living truth-base accurate and current. The value is automated freshness instead of manual re-verification.

## Approach

A PowerShell orchestration loop that triggers the local orchestration layer (Phase 2) for multi-round tasks and writes results to a morning briefing.

- Orchestration: PowerShell 7.
- Reasoning: Qwen (tooling) and DeepSeek-R1 (reasoning).
- Reporting: Markdown morning briefing.
- Scheduling: Windows Task Scheduler.

## Ordered steps

### Task 1: Morning briefing foundation

Create `.ai/templates/morning-briefing.md` and an audit-history log.

- [x] Create the briefing template for verified changes, identified drift, and pending decisions.
- [x] Initialize a machine-readable audit-history log tracking nightly pass rates.

### Task 2: The Nightly Steward core script

Create `.ai/scripts/steward.ps1`.

- [x] Implement drift-check logic that reads each `.ai/context/*.md`, extracts its `verification_cmd`, and runs it.
- [x] Implement consensus capture: on command failure, flag the drift into the briefing instead of failing the whole run.
- [x] Integrate with the local gateway for tasks requiring tool-calling.

### Task 3: Horizon-scanning routine

Modify `.ai/skills/horizon-scanning/SKILL.md`; create `.ai/scripts/scan_horizon.py`.

- [x] Automate research for new 2026 models and MCP servers.
- [x] Propose an ADR 002 update when a superior model tier is found.

### Task 4: Knowledge CI safety hook

Create a pre-commit hook for the workspace repo.

- [x] Implement a truth-validator hook that blocks commits when `.ai/` context was not updated in the same session.

### Task 5: Loop verification

- [x] Run a manual steward audit and verify the generated morning briefing.
- [x] **Step 2: Commit Phase 3 Completion** — *historical; completed 2026-03. Original command preserved verbatim (this 2026-06 standardization pass commits centrally and never `git add -A`):*

```bash
git add .
git commit -m "feat: complete phase 3 learning and maintenance loop"
```

## Retrospective

Updates hb-doc.2.

Outcome: implemented in 2026-03. `.ai/scripts/steward.ps1` and `.ai/scripts/scan_horizon.py` exist; the `horizon-scanning` skill is live at `.ai/skills/horizon-scanning/`. A morning briefing was produced (`docs/superpowers/maintenance/2026-03-25-briefing.md`), and that first run surfaced a real drift signal (a `docker --version` verification command failing because Docker is not installed on this host) — the consensus-capture behavior worked as designed. The original git-commit step is recorded as completed; commits are handled centrally. Retained as a historical record.
