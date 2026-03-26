# ADR 003: Local Script Autonomy & Sandboxing

**Date:** 2026-03-25  
**Status:** ✅ Accepted  
**Agent:** Gemini CLI (Architect)

## Context
Executing scripts via cloud agents (metered tokens) is inefficient and costly. We need a way for the local reasoning model to write and run its own automation scripts securely and at zero cost.

## Decision
We will implement a **Local Compute Sandbox** using the following protocol:
1.  **Tooling**: Use `code-sandbox-mcp` (Python) or `sandbox-mcp` (Multi-language) as the execution engine.
2.  **Isolation**: All scripts must run in a containerized environment (Docker/Podman) to prevent accidental modification of work repositories.
3.  **Delegation**: The cloud agent is **FORBIDDEN** from writing execution scripts. It must instead delegate the *Scripting Goal* to the local model.

## Rationale
- **Cost Efficiency**: Zero metered tokens for the "Write-Run-Debug" loop.
- **Safety**: Containers enforce our "Read-Only" boundaries for the `malachite/` and `architecture/` repos.
- **Rigor**: Local models (like DeepSeek-R1) are specifically tuned for iterative coding and debugging.

## Verification (The Proof)
- Research (March 25, 2026) confirmed `llm-sandbox` as the industry-leading pattern for local model code execution.

## Consequences
- The workspace must have Docker or Podman installed.
- The `mcp-config.json` must include a `sandbox` server.
- The cloud agent must pivot from "I will write a script" to "Local Agent, write a script to achieve X."
