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

## Technical Details
See [the hand-off guide](references/HANDOFF_GUIDE.md) for command patterns and model-specific tuning.
