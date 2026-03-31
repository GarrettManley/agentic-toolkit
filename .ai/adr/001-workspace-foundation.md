# ADR 001: Architecture of Hybrid Context Synthesis

**Date:** 2026-03-25  
**Status:** ✅ Accepted  
**Agent:** Gemini CLI (Architect)  
**Trace ID:** `trace-20260325-001`

## Context
We are establishing the "Architecture of Hybrid Context Synthesis" to manage knowledge across multiple project repos. We need a system that is:
1. Agent-agnostic (Standard Markdown).
2. Hierarchical (Global + Local inheritance).
3. Verified (Empirical Code Proof + Authoritative Web Proof).
4. Token-Budgeted (Efficient discovery protocols).

## Decision
We will implement a dual-tier `.ai/` directory structure for Hybrid Context Synthesis. All "Facts" must undergo **Mandatory Verification Discovery** before commitment.

### Hybrid Orchestration Stack (Vetted 2026-03-25)
- **Model**: `deepseek-r1` via Ollama (Reasoning).
- **Protocol**: Token-budgeted discovery (Minimize context bloat).
- **Verification**: Mandatory traces (Terminal/Web proof).

## Verification (The Proof)
*   **Empirical Proof:** Success of `write_file` on 2026-03-25 confirmed the workspace root is writable.
*   **Referential Proof:** Consensus reached in conversation history (March 25, 2026).

## Consequences
- Agents must now check `/.ai/context/` before proposing changes.
- All new architectural decisions must be recorded in `/.ai/adr/`.
- Knowledge drift must be audited via `verification_cmd` logic.
