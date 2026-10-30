---
topic: Workspace Conventions
last_verified: 2026-10-29
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "dir"
evidence: "docs/standards/solid-clean-architecture.md committed on feat/hb-w4h-1-architecture-standard, 2026-10-29"
model_used: Claude Sonnet 5.5
---

# Global Workspace Conventions

Standard engineering practices for all repositories in this workspace.

## 1. Documentation
- All projects must have a `README.md`.
- Major architectural choices must have an ADR in `/.ai/adr/`.
- Project-specific facts live in `/.ai/context/`.

## 2. Agentic Engineering
- Agents should use their search/glob tools (Grep/Glob in Claude Code,
  `grep_search`/`glob` in Gemini CLI) to verify context before acting.
- Findings must be shared across sessions via the `.remember/remember.md` handoff
  and, cross-tool, the memory-sync protocol (`memory-sync.md` → canonical copy).
- Cost-aware orchestration is required (prefer local/free models for research).

## 3. Technology Standards
- **.NET**: Preferred for enterprise backends.
- **Python**: Preferred for automation and utility scripts.
- **Node.js/Vite**: Preferred for modern front-end applications.
- **Flutter**: Preferred for cross-platform mobile apps.

## 4. Software design

- The workspace architecture standard (SOLID + Clean Architecture) is `docs/standards/solid-clean-architecture.md`.
- The reviewer checklist there is the architecture gate for every `/deliver` run.
