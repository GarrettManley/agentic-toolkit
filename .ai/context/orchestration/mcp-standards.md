---
topic: MCP Port & Gateway Standards
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "Get-NetTCPConnection -LocalPort 8000"
evidence: "Confirmed port 8000 is reserved for ollama-mcp-bridge"
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

## 3. Tool Discovery
- The Gateway (8000) is responsible for aggregating all tools into a single `/api/chat` endpoint.
- Clients must point to `http://localhost:8000` to access the full toolset.
