---
topic: Hardware Profile & Model Optimization
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "nvidia-smi; Get-CimInstance Win32_Processor"
evidence: "RTX 4060 8GB VRAM detected"
model_used: Gemini Pro
---

# Hardware Profile

This profile defines the local compute constraints for agentic orchestration.

## 1. System Specs
- **CPU**: Intel(R) Core(TM) i7-14700F (20 Cores / 28 Threads).
- **RAM**: 32 GB Physical Memory.
- **GPU**: NVIDIA GeForce RTX 4060 (8 GB Dedicated VRAM).

## 2. Model Optimization (The 8B Sweet Spot)
Based on Tier 1 benchmarks, the following orchestration strategy is enforced:

| Tier | Model | Strategy | VRAM Usage |
| :--- | :--- | :--- | :--- |
| **Primary** | `deepseek-r1-tool-calling:8b` | **Full GPU Offload**. Target for 100% of reasoning tasks. | ~5.6 GB |
| **Fallback** | `deepseek-r1-tool-calling:14b` | **Partial Offload**. Only for complex logic; expect < 5 t/s. | ~10 GB (OOM Risk) |

## 3. Tool Performance
- **Search**: `everything-search-mcp` is recommended over heavy vector DBs due to the high-performance i7 CPU.
- **Inference**: Target speed is > 40 tokens/sec on the 8B model.
