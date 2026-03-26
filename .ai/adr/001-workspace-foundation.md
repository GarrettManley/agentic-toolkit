# ADR 001: Workspace Foundation & Truth Protocol

**Date:** 2026-03-25  
**Status:** ✅ Accepted  
**Agent:** Gemini CLI (Architect)

## Context
We are establishing a "best-in-class" agentic workspace across multiple project repos. We need a way to store knowledge that is:
1. Agent-agnostic (Standard Markdown).
2. Hierarchical (Global + Local inheritance).
3. Verified (Empirical Code Proof + Authoritative Web Proof).
4. Cost-Aware (Tiered model usage).

## Decision
We will implement a dual-tier `.ai/` directory structure. All "Facts" will be stored in fragmented Markdown files with YAML metadata for verification tracking.

### Local Orchestration Stack (Vetted 2026-03-25)
- **Model**: `deepseek-r1` via Ollama.
- **Orchestrator**: `deepseek-thinker-mcp` (Reasoning preservation).
- **Search**: `everything-search-mcp` (Native OS indexing).
- **Bridge**: `ollama-mcp-bridge` (Tool enablement).

## Verification (The Proof)
*   **Empirical Proof:** Success of `write_file` on 2026-03-25 confirmed the workspace root is writable.
*   **Referential Proof:** Consensus reached in conversation history (March 25, 2026).

## Consequences
- Agents must now check `/.ai/context/` before proposing changes.
- All new architectural decisions must be recorded in `/.ai/adr/`.
- Knowledge drift must be audited via `verification_cmd` logic.
