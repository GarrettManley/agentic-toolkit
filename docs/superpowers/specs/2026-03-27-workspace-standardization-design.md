# Workspace Standardization Design

**Owner:** Garrett Manley · **Date:** 2026-03-27 · **Status:** Superseded (historical) · **Tracker:** hb-doc.2

This design proposed standardizing the workspace structure and lifecycle so any agent — Gemini, Claude, or Ollama — follows the same rigorous process. It is retained as a historical record; the directory layout below describes the *intended* design, which the implemented workspace only partially adopted (see Revision history).

## Overview

The design implements a "contractor" model for AI agents. It treats the workspace as an active agentic operating system in which assistants follow a standard lifecycle: brief, spec, execution, verification.

## Scope

- **In scope:** the `.ai/` knowledge kernel, root agent-config overlays, the task lifecycle, and steward automation.
- **Out of scope:** corporate and external repositories, which are isolated and read-only.

## System overview

The `.ai/` directory serves as the kernel of the workspace. The tree below is the originally proposed layout.

```text
C:\Users\Garre\Workspace\
├── GEMINI.md (agent-config overlay)
├── .ai/
│   ├── adr/ (architectural decision records)
│   ├── context/ (standards, maintenance logs, orchestration status)
│   ├── agents/ (model-tier definitions)
│   ├── skills/ (truth-seeker, citation-seeker, horizon-scanning, local-orchestrator)
│   ├── scripts/ (steward.ps1, generate_spec.py, refine_content.py, ...)
│   ├── templates/ (spec, briefing, blog templates)
│   └── logs/ (reasoning traces for evaluation)
└── docs/superpowers/specs/ (permanent home for signed-off designs)
```

## Design details

### Bootstrap protocol

Assistants are oriented through a root-level agent-config overlay into the `.ai/` standards.

- **Tiered context loading:** agents read a short summary first and load specific standards (for example Firebase or Python) only when the task requires them, saving tokens.
- **Repository orientation:** agents consult the workspace project index to understand directory boundaries and avoid hallucinating paths.

### Fast-track protocol

- **Low-complexity tasks:** typo fixes and single-line changes bypass the staging area.
- **High-complexity tasks:** architectural or multi-file changes require a brief in the task-context staging area before work begins.

### Role personas

Roles are assumed through system instructions stored under `.ai/`.

- **Scaffolder (producer):** implements features against a spec.
- **Critic (senior reviewer):** reviews work for hallucinations and standards compliance.
- **Quality guard:** drives TDD and automated verification.

### Task lifecycle (the contractor model)

1. **Briefing:** the human or steward creates a task brief.
2. **Design:** the agent drafts a spec. Gate: human approval.
3. **Plan:** the agent writes an implementation plan.
4. **Act:** the agent executes in iterative plan, act, validate cycles.
5. **Critique:** a critic persona reviews the trajectory and diff.
6. **Archival:** the steward moves the spec to `docs/` and clears the staging area.

### Stewardship and automation

The steward script (`.ai/scripts/steward.ps1` / `steward.py`) acts as the operating-system manager.

- **Session locking:** prevents concurrent model conflicts on the same task.
- **Trajectory pruning:** rotates logs to keep the repo clean.
- **Context assembly:** compiles the briefing package for the model.

## Dependencies

- Ollama with local reasoning and tooling models.
- The `.ai/` skills and ADR set.
- PowerShell 7 and Python (`uv`) for steward automation.

## References

- ADR `002-local-orchestration.md`.
- `docs/superpowers/plans/2026-03-25-local-orchestration-engine.md`.

## Revision history

| Date | Change |
| :--- | :--- |
| 2026-03-27 | Original proposal (status: proposed). |
| 2026-06-01 | Marked superseded. Reconciled to as-built reality: the steward lives at `.ai/scripts/steward.py` (not `toolkit/`); the `.ai/` tree uses `adr/`, `context/`, `agents/`, `skills/`, `scripts/`, `templates/`, `logs/` rather than a `core/` subtree with per-agent `.md` cards; the root carries a single `GEMINI.md` overlay rather than three shims. |
