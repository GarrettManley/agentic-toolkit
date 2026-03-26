---
topic: Workspace Conventions
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "dir"
evidence: "Manual inspection of project folders"
model_used: Gemini Pro
---

# Global Workspace Conventions

Standard engineering practices for all repositories in this workspace.

## 1. Documentation
- All projects must have a `README.md`.
- Major architectural choices must have an ADR in `/.ai/adr/`.
- Project-specific facts live in `/.ai/context/`.

## 2. Agentic Engineering
- Agents should use `grep_search` and `glob` to verify context before acting.
- Findings must be shared across sessions via the "State-Sync" protocol.
- Cost-aware orchestration is required (prefer local/free models for research).

## 3. Technology Standards
- **.NET**: Preferred for enterprise backends.
- **Python**: Preferred for automation and utility scripts.
- **Node.js/Vite**: Preferred for modern front-end applications.
- **Flutter**: Preferred for cross-platform mobile apps.
