---
topic: Agentic Autonomy & Permissions
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "git --version"
evidence: "Environment allows git operations"
model_used: Gemini Pro
---

# Agentic Autonomy & Permissions

This standard defines the "Verified-Trust" model for agents in this workspace.

## 1. File System Operations
- **Creation/Editing**: Permitted for all workspace configuration files (`.ai/`, `docs/`).
- **Strict Read-Only**: The `malachite/` and `architecture/` repositories are **Authoritative Work Sources**. Agents are **FORBIDDEN** from writing to, deleting from, or modifying these directories.
- **Proposal Model**: If an agent identifies a fix or improvement in a work repo, it must document the finding in `.ai/context/` and present a plan for the user to execute manually.

## 2. Version Control (Git)
- **Commits**: Permitted **only** for files in the `.ai/` directory (Context, ADRs, Skills).
- **Code Commits**: Agents should propose a commit command for the user to run, unless specifically granted "Auto-Commit" for a task.

## 3. Tool Execution
- **Allowed**: Any non-sudo command required for "Proof of Truth" (build, test, lint, grep).
- **Escalation**: If a command requires `sudo` or system-level modification, the agent **must** log it to the "Morning Briefing" for user intervention.
