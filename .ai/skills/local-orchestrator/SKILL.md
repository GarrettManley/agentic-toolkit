---
name: local-orchestrator
description: Guides the hand-off to local models within the Architecture of Hybrid Context Synthesis. Use for multi-file searches or high-volume log compaction.
compatibility: Requires Ollama, DeepSeek-R1 (8B or 14B), and ollama-mcp-bridge.
metadata:
  version: "1.2.0"
  author: Agentic Architect
---

# Local-Orchestrator Skill

This skill optimizes the Architecture of Hybrid Context Synthesis by offloading reasoning to local hardware.

## Core Directives

### 1. Hand-Off Criteria
Hand off a task if it matches any of the following:
- **Search Intensity**: Requires searching > 10 files.
- **Reasoning Depth**: Requires a multi-round "Thought Loop" to resolve an ambiguity.
- **Data Volume**: Summarizing or compacting session history into permanent context.

### 2. Orchestration Protocol
When triggering a hand-off:
1.  **Planning Phase (Reasoning Tier)**: Request a `task-plan.json` from the Reasoning Tier model.
2.  **Execution Phase (Tooling Tier)**: Pass the plan to the Tooling Tier for implementation.
3.  **Critique Phase (Reasoning Tier)**: The Reasoning Tier MUST perform an adversarial review of the implemented code against `conventions.md`.
4.  **Final Synthesis**: Combine the implementation, critique, and verification results for the Supervisor.

## Technical Directives

### 1. Producer-Critic Command Loop
When performing complex edits, use this interleaved pattern:
```powershell
# Step 1: Implementation (Producer)
$code = Invoke-RestMethod -Uri "http://localhost:8000/api/chat" -Body (@{ model = "tooling-tier"; messages = @(...) } | ConvertTo-Json)

# Step 2: Critique (Critic)
$critique = Invoke-RestMethod -Uri "http://localhost:8000/api/chat" -Body (@{ model = "reasoning-tier"; messages = @(@{ role = "user"; content = "Review this code: $code" }) } | ConvertTo-Json)
```

### 2. Return Synthesis
After receiving a response from the local model:
- **Thought Capture**: Extract the `<think>` block to understand the local reasoning chain.
- **Evidence Verification**: The result MUST contain a shell command or web excerpt to be valid.
- **State-Sync**: Update the global `.ai/context/` if the local agent discovered a new fact.
