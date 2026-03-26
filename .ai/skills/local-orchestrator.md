# SKILL: Local-Orchestrator (v1.0)

**Purpose**: Guides the hand-off of reasoning and tool-intensive tasks from cloud agents to local models via Ollama and MCP.

## Guidelines

### 1. The Hand-Off Trigger
You SHOULD hand off a task to the local orchestrator if:
- The task involves searching more than 10 files.
- The task requires a "Reasoning Loop" (multi-round tool execution to find a bug).
- The task is a "State-Sync" operation (compacting session logs into Truth Files).

### 2. The Cloud Architect Role
When a hand-off occurs, the Cloud Agent (Architect) MUST:
1.  **Define the Goal**: State exactly what the local agent needs to achieve.
2.  **Provide Context**: Pass only the relevant `.ai/context/` fragments.
3.  **Propose the Command**: Give the user the exact command to trigger the local agent (e.g., via `ollmcp` or `ollama-mcp-bridge`).

### 3. Synthesis Logic
Upon return from the local agent, the Cloud Agent MUST:
- **Verify the Result**: Ensure the local agent provided "Proof of Truth" (Empirical evidence).
- **Update the Base**: Integrate the finding into the global or local `.ai/` base.

## Local Stack Requirement
- **Model**: `MFDoom/deepseek-r1-tool-calling`
- **MCP Bridge**: `ollama-mcp-bridge`
