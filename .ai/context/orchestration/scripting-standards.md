---
topic: Cross-Platform Scripting Standards
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "docker --version"
evidence: "Docker selected as universal compute backend"
model_used: Gemini Pro
---

# Scripting Standards

This document enforces platform-agnostic automation for all agents in this workspace.

## 1. The Agnostic Mandate
Agents are **FORBIDDEN** from writing automation that relies on OS-specific subsystems (e.g., WSL2, Homebrew, chocolatey) unless explicitly requested for a host-level maintenance task.

## 2. Universal Compute Sandbox
All agent-generated scripts MUST execute within a standard Docker container:
- **Default Image**: `python:3.12-slim` or `node:20-slim`.
- **Isolation**: Containers must run with `--network=none` unless external data is required.
- **Persistence**: Temporary script artifacts must be deleted after the "Synthesis" phase.

## 3. Tool Communication
Automation results must be returned as standardized JSON objects to the primary orchestrator to ensure compatibility between Gemini, Claude, and local models.
