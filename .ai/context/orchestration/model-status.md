---
topic: Local Model Baseline
last_verified: 2026-06-09
model: deepseek-r1-8b-agent (MFDoom distilled)
optimized_ctx: 4096
vram_offload: Full GPU (RTX 4060)
inference_speed: 54.05 tokens/sec
status: ⚠️ STALE — model no longer installed (verified via `ollama list` 2026-06-09)
---

# Local Model Status

> **STALE (2026-06-09):** `deepseek-r1-8b-agent` / `MFDoom/deepseek-r1-tool-calling:8b` is
> no longer in `ollama list`. Current reasoning primary is `deepseek-r1:7b` — see canonical
> `~/.claude/context/hardware-profile.md`. The benchmark below is retained as a historical
> record only.

This document records the verified performance of the local reasoning engine.

## 1. Verified Model
- **Name**: `deepseek-r1-8b-agent`
- **Source**: `MFDoom/deepseek-r1-tool-calling:8b`
- **Quantization**: 4-bit (Standard Ollama).

## 2. Benchmark Results (2026-03-25)
- **Prompt Eval**: 341.26 tokens/s
- **Response Eval**: 54.05 tokens/s
- **Memory Impact**: ~5.2 GB VRAM.

## 3. Configuration
- **Context Window**: 4096 (Hard limit to prevent VRAM overflow).
- **GPU Offload**: 99 Layers (Full).
- **Temperature**: 0.1 (Precision focus).
