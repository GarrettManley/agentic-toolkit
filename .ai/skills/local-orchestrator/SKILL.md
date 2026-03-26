---
name: local-orchestrator
description: Guides the hand-off of reasoning and tool-intensive tasks from cloud agents to local models via Ollama and MCP. Use when tasks involve multi-file searches, complex debugging loops, or high-volume log compaction.
compatibility: Requires Ollama, DeepSeek-R1 (8B or 14B), and ollama-mcp-bridge.
metadata:
  version: "1.1.0"
  author: Agentic Architect
---

# Local-Orchestrator Skill

This skill optimizes workspace efficiency by offloading reasoning to local hardware.

## Core Directives

### 1. Hand-Off Criteria
Hand off a task if it matches any of the following:
- **Search Intensity**: Requires searching > 10 files.
- **Reasoning Depth**: Requires a multi-round "Thought Loop" to resolve an ambiguity.
- **Data Volume**: Summarizing or compacting session history into permanent context.

### 2. Orchestration Protocol
When triggering a hand-off:
1.  **Scope**: Define the atomic goal for the local agent.
2.  **Context**: Provide only the necessary context fragments.
3.  **Command**: Propose the exact command for the user to trigger local inference.

## Technical Directives

### 1. Local Hand-Off Command
When proposing a hand-off, use the following PowerShell 7 template:
```powershell
# Send task to local DeepSeek-R1 (8B) via the Gateway
Invoke-RestMethod -Uri "http://localhost:8000/api/chat" -Method Post -Body (@{
    model = "deepseek-r1-8b-agent"
    messages = @(@{ role = "user"; content = "TASK_DESCRIPTION" })
} | ConvertTo-Json)
```

### 2. Return Synthesis
After receiving a response from the local model:
- **Thought Capture**: Extract the `<think>` block to understand the local reasoning chain.
- **Evidence Verification**: The result MUST contain a shell command or web excerpt to be valid.
- **State-Sync**: Update the global `.ai/context/` if the local agent discovered a new fact.
