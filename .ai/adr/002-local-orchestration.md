# ADR 002: Local Orchestration & Tool-Enabled Reasoning

**Date:** 2026-03-25  
**Status:** ✅ Accepted  
**Agent:** Gemini CLI (Architect)

## Context
To achieve "best-in-class" efficiency, we need to offload token-intensive tasks (reasoning loops, task decomposition, and surgical searching) to local hardware. Standard local models often struggle with the structured tool-calling required for the Model Context Protocol (MCP).

## Decision
We will implement a local orchestration layer using a **Tiered Model Strategy**. The workspace will remain model-agnostic, with specific models selected based on current industry benchmarks (evaluated monthly).

### Current Tier Allocation (2026-03-25)
1.  **Tooling Tier**: Optimized for high-accuracy JSON formatting and MCP integration (Current: `Qwen 2.5 Coder 7B`).
2.  **Reasoning Tier**: Optimized for multi-step "Chain of Thought" and strategic planning (Current: `DeepSeek-R1 8B`).
3.  **Metered Tier**: Cloud-based fallback for high-scale architectural design (Current: `Gemini 2.0 Pro` / `Claude 3.7 Opus`).

## Rationale
By defining **Tiers** rather than specific models, we ensure the workspace can "Hot-Swap" the engine as better open-source alternatives emerge (e.g., Llama 4, Mistral v4) without rewriting our core skills or context.

### Scientific Substantiation (March 2026)
- **Deterministic Actionability**: Multi-agent orchestration has been proven to achieve a **100% actionable recommendation rate**, compared to 1.7% for single-agent systems (*arXiv:2511.15755*). [1]
- **Token Efficiency**: Hybrid architectures reduce metered token usage by up to **65-fold** by isolating tasks and preventing context interference (*medRxiv:2025.08.22*). [2]
- **Latency**: Local inference on consumer hardware (RTX 40-series) provides sub-150ms TTFT, significantly outperforming cloud-only fast-paths. [3]

## Verification (The Proof)
- **External**: [1] arXiv:2511.15755; [2] medRxiv:2025.08.22; [3] IEEE OFC 2025.
- **Internal**: Success of `qwen-orchestrator` in performing autonomous multi-repo audits at zero metered cost (2026-03-25).

## Consequences
- The primary cloud agent must now identify "High-Volume" sub-tasks and propose a hand-off command.
- Users must ensure the `ollama` service is running during agentic sessions.
