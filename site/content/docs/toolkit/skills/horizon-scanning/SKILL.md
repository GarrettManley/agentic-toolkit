---
title: "Agent Skill: horizon-scanning / SKILL.md"
date: 2026-03-30
draft: false
---

# Agent Skill: horizon-scanning / SKILL.md

```text
---
name: horizon-scanning
description: Periodically researches Tier 1 authoritative sources to identify the "Latest and Greatest" models and MCP servers. Use when the user asks "What's new?" or when a "Re-evaluation Schedule" is triggered in the context.
compatibility: Requires web_fetch and google_web_search tools.
metadata:
  version: "1.0.0"
  author: Agentic Architect
---

# Horizon Scanning Skill

This skill ensures the workspace stays "Best-in-Class" by preventing model lock-in and providing the latest SOTA insights into the **Architecture of Hybrid Context Synthesis**.

## Core Directives

### 1. The Scanning Protocol
When triggered, you MUST:
- Search for "State of the Art (SOTA) 7B-14B local models" for tool-calling.
- Check the [MCP Server Gallery](https://github.com/modelcontextprotocol/servers) for new industry integrations.
- Compare current "Model Status" benchmarks against new research.

### 2. The Re-evaluation Logic
If a new model consistently outperforms our current "Tooling" or "Reasoning" tier in Tier 1 benchmarks:
1.  **Plan**: Propose a load-test implementation plan.
2.  **Vet**: Perform a cross-project audit with the new model.
3.  **Swap**: Update the Tier Allocation in ADR 002.

## Authoritative Sources
- **Hugging Face Open LLM Leaderboard**.
- **Ollama Library** (New releases).
- **Anthropic / OpenAI / Google** developer blogs.

```

---
*Published from .ai active toolkit.*
