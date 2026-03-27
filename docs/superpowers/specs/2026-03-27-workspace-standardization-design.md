# Workspace Standardization: The Agentic Operating System

**Date:** 2026-03-27  
**Status:** PROPOSED  
**Goal:** Standardize workspace structure and process for seamless, rigorous use across Gemini, Claude, and Ollama, adhering to "Agentic Design Patterns" best practices.

## 1. Overview
This design implements a "Contractor" model for AI agents. It transforms the workspace from a passive file collection into an active "Agentic OS" where assistants follow a standardized lifecycle of **Brief -> Spec -> Execution -> Verification**.

## 2. Directory Architecture
The `.ai` directory serves as the "Kernel" of the workspace.

```text
C:\Users\Garre\Workspace\
├── GEMINI.md (Shim)
├── CLAUDE.md (Shim)
├── AGENTS.md (Shim)
├── .ai/
│   ├── core/
│   │   ├── bootstrap.md (Mandatory first read: Constitution)
│   │   ├── projects.md (Monorepo Index & Dependency Map)
│   │   └── standards/ (Language & Infrastructure rules)
│   ├── agents/
│   │   ├── scaffolder.md (Agent Card: Producer)
│   │   ├── critic.md (Agent Card: Senior Reviewer)
│   │   └── test-engineer.md (Agent Card: Quality Guard)
│   ├── prompts/ (Version-controlled shared snippet library)
│   ├── task_context/ (Staging Area for active sessions)
│   └── logs/
│       └── trajectories/ (Reasoning traces for evaluation)
└── docs/superpowers/specs/ (Permanent home for signed-off designs)
```

## 3. Core Protocols

### 3.1. The Bootstrap Protocol
All assistants are redirected via root-level "shims" to `.ai/core/bootstrap.md`.
*   **Tiered Context Loading:** Agents read a 1-page summary first. They only load specific standards (e.g., Firebase, Python) when the task scope requires it to save tokens.
*   **Monorepo Orientation:** Agents refer to `.ai/core/projects.md` to understand directory boundaries and avoid "hallucinating" paths.

### 3.2. The "Fast-Track" Protocol (Layman Synthesis)
*   **Low-Complexity Tasks:** Minor edits (typos, single-line changes) bypass the `task_context` staging area.
*   **High-Complexity Tasks:** Any task involving architectural changes or multiple files requires a `01_BRIEF.md` in `.ai/task_context/`.

## 4. Role Personas (Agent Cards)
Roles are assumed via specific system instructions stored in `.ai/agents/`.
*   **The Scaffolder (Producer):** Implements features against a spec.
*   **The Critic (Senior Principal):** Meticulously reviews work for "hallucinations" and standard compliance.
*   **The Quality Guard:** Implements TDD and automated verification.

## 5. Task Lifecycle (The Contractor Model)
1.  **Briefing:** Human/Steward creates `.ai/task_context/01_BRIEF.md`.
2.  **Design:** Agent creates `.ai/task_context/02_SPEC.md`. **GATE:** Human Approval.
3.  **Plan:** Agent creates an implementation plan.
4.  **Act:** Agent executes in iterative "Plan -> Act -> Validate" cycles.
5.  **Critique:** A "Critic" persona reviews the trajectory and diff.
6.  **Archival:** Steward moves the Spec to `docs/` and clears the staging area.

## 6. Stewardship & Automation
The `toolkit/steward.py` script is enhanced to act as the "OS Manager":
*   **Session Locking:** Creates a `.lock` file in `task_context/` to prevent model conflicts.
*   **Trajectory Pruning:** Rotates logs to keep the repo clean.
*   **Context Assembly:** Automatically compiles the "Briefing Package" for the model.

## 7. Success Criteria
*   **Consistency:** Every model (regardless of UI) follows the same core security and coding mandates.
*   **Traceability:** Every major change is backed by a Spec and a Trajectory Log.
*   **Efficiency:** Context is strictly scoped to the active task, reducing token waste and "drift."
