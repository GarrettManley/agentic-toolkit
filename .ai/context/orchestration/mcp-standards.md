---
topic: MCP Port & Gateway Standards
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "Invoke-RestMethod -Uri http://localhost:8000/health"
evidence: "Verified bridge health endpoint is responsive"
model_used: Gemini Pro
---

# MCP Standards

Standardized communication patterns for local Model Context Protocol (MCP) servers.

## 1. Port Allocation Strategy
To prevent collisions, the following port hierarchy is enforced in this workspace:

| Port Range | Service Type | Example |
| :--- | :--- | :--- |
| **8000** | **Primary Gateway** | `ollama-mcp-bridge` |
| **3000-3099** | **SSE Web Tier** | `github-mcp`, `drive-mcp` |
| **8001-8099** | **Secondary Proxies** | `mcp-proxy`, `litellm` |

## 2. Server Configuration
- All servers must be defined in `/.ai/context/orchestration/mcp-config.json`.
- Prefer `stdio` transport for internal workspace tools (`filesystem`, `search`).
- Use `SSE` transport only for external/remote integrations.

## 4. Scripting & Automation Standards
To minimize metered token usage, all script execution follows the **"Local Builder"** pattern:
- **Sandbox Requirement**: All agent-generated scripts MUST execute within a containerized MCP sandbox.
- **Prohibited Tools**: The primary cloud agent should avoid using `run_shell_command` for complex automation, preferring to delegate the goal to the Local Orchestrator.
- **Tool Mapping**: The sandbox must have read-only mounts to work repositories (`/malachite`) and read-write access to `.ai/context`.
