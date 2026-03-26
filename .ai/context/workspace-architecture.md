---
topic: Workspace Architecture
last_verified: 2026-03-25 22:58:00
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "dir .ai -Recurse; git ls-files .ai"
evidence: "10 files confirmed in physical storage and Git index."
model_used: Gemini Pro
---

# Workspace Architecture Truth

This workspace follows a hierarchical agentic design with strict data boundaries.

## 1. Directory Tiers
- **Tier A: Workspace Config (`/.ai/`, `docs/`)**: Writable by agents. Contains ADRs, Skills, and Context.
- **Tier B: Work Repos (`/malachite/`, `/architecture/`)**: **READ-ONLY**. These are external "work files" used for authoritative context but never modified by agentic tasks.
- **Tier C: Local Context (`[project]/.ai/`)**: Writable by agents. Contains project-specific overrides.

## The Proof Protocol
1.  **Code Truth:** Proven via terminal output.
2.  **Web Truth:** Proven via Tier 1 (Official) or Tier 2 (Expert) sources.
3.  **Tier 3:** Used for leads only; never committed as "Truth."
