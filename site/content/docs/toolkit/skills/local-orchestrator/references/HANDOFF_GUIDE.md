---
title: "Agent Skill: local-orchestrator / references / HANDOFF_GUIDE.md"
date: 2026-03-30
draft: false
---

# Agent Skill: local-orchestrator / references / HANDOFF_GUIDE.md

```text
# Local Hand-Off Guide

## Model Tuning (RTX 4060 / 8GB VRAM)

### Primary Model
`MFDoom/deepseek-r1-tool-calling:8b`
- **Tuning**: Full GPU Offload.
- **Speed**: > 40 tokens/sec.

### Fallback Model
`deepseek-r1-tool-calling:14b`
- **Tuning**: Partial CPU Offload.
- **Speed**: < 5 tokens/sec.

## Tool Command Patterns

### Pulling the Model
```powershell
ollama pull MFDoom/deepseek-r1-tool-calling:8b
```

### Local Audit Trigger
```powershell
# Propose this to the user for local search
uvx everything-search-mcp search "pattern"
```

```

---
*Published from .ai active toolkit.*
