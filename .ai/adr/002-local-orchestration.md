# ADR 002: Local Orchestration & Tool-Enabled Reasoning

**Date:** 2026-03-25  
**Status:** ✅ Accepted  
**Agent:** Gemini CLI (Architect)

## Context
To achieve "best-in-class" efficiency, we need to offload token-intensive tasks (reasoning loops, task decomposition, and surgical searching) to local hardware. Standard local models often struggle with the structured tool-calling required for the Model Context Protocol (MCP).

## Decision
We will implement a local orchestration layer using the following stack:
1.  **Primary Local Model**: `MFDoom/deepseek-r1-tool-calling` (quantized as appropriate for the machine's VRAM).
2.  **MCP Integration**: `ollama-mcp-bridge` to bridge local inference with workspace tools.
3.  **Discovery Logic**: A "Local-First" protocol where the cloud agent acts as the *Architect* and the local agent acts as the *Specialized Builder*.

## Rationale
- **Cost**: Reduces metered token usage for repetitive reasoning steps.
- **Privacy**: Keeps sensitive local file indices on-machine.
- **Performance**: High-speed OS-native searching via `everything-search-mcp`.

## Verification (The Proof)
- Tier 1/2 Research (March 25, 2026) confirmed these as the most stable open-source solutions for 2026 workflows.
- Success of local `ollama` version check (Pending).

## Consequences
- The primary cloud agent must now identify "High-Volume" sub-tasks and propose a hand-off command.
- Users must ensure the `ollama` service is running during agentic sessions.
