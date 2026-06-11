---
topic: Agentic Autonomy & Permissions
last_verified: 2026-06-09
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "git --version"
evidence: "Corporate-root list reconciled to dir listing 2026-06-09 (Duracell*, no malachite/architecture present)"
model_used: Claude Fable 5
---

# Agentic Autonomy & Permissions

This standard defines the "Verified-Trust" model for agents in this workspace.

## 1. File System Operations
- **Creation/Editing**: Permitted for all workspace configuration files (`.ai/`, `docs/`).
- **Strict Read-Only**: The corporate work repositories are **Authoritative Work Sources**. Agents are **FORBIDDEN** from writing to, deleting from, modifying, or even scanning these directories unless explicitly directed for a specific task.
- **Proposal Model**: If an agent identifies a fix or improvement in a work repo, it must document the finding in `.ai/context/` and present a plan for the user to execute manually.

## 2. Version Control (Git)
- **Commits**: Permitted **only** for files in the `.ai/` directory (Context, ADRs, Skills).
- **Code Commits**: Agents should propose a commit command for the user to run, unless specifically granted "Auto-Commit" for a task.

## 3. Tool Execution
- **Allowed**: Any non-sudo command required for "Proof of Truth" (build, test, lint, grep).
- **Escalation**: If a command requires `sudo` or system-level modification, the agent **must** log it to the "Morning Briefing" for user intervention.
