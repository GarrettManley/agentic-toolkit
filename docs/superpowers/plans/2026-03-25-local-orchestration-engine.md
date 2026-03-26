# Local Orchestration Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Offload reasoning, task decomposition, and high-volume searches to local hardware (RTX 4060) to minimize metered token usage and improve privacy.

**Architecture:** A "Cloud Architect / Local Builder" model. The primary agent (Gemini/Claude) acts as the Architect, identifying complex sub-tasks and handing them off to a local DeepSeek-R1 (8B) instance via the Model Context Protocol (MCP).

**Tech Stack:** 
- **Inference**: Ollama + `MFDoom/deepseek-r1-tool-calling:8b`
- **Bridge**: `ollama-mcp-bridge`
- **Indexing**: `everything-search-mcp`
- **Validation**: `uvx` (Python) / `npx` (Node.js)

---

### Task 1: Reasoning Model Preparation

**Files:**
- Create: `.ai/context/orchestration/model-status.md`
- Modify: `.ai/adr/002-local-orchestration.md`

- [ ] **Step 1: Pull the tool-calling optimized model**
Run: `ollama pull MFDoom/deepseek-r1-tool-calling:8b`
Expected: Download completes successfully.

- [ ] **Step 2: Verify local inference speed**
Run: `ollama run MFDoom/deepseek-r1-tool-calling:8b "Write a hello world in C# and explain why you chose the namespace."`
Expected: Response generates at > 30 tokens/sec.

- [ ] **Step 3: Document Model Baseline**
Create `.ai/context/orchestration/model-status.md` with:
```markdown
---
topic: Local Model Baseline
last_verified: 2026-03-25
model: deepseek-r1-tool-calling:8b
speed_test: [Tokens/Sec]
---
```

---

### Task 2: MCP Bridge Configuration

**Files:**
- Create: `.ai/context/orchestration/mcp-config.md`
- Test: `.ai/scripts/test-bridge.ps1`

- [ ] **Step 1: Install the Ollama-MCP Bridge**
Run: `npm install -g ollama-mcp-bridge`
Expected: CLI tool `ollama-mcp-bridge` is in PATH.

- [ ] **Step 2: Research Bridge Configuration**
Run: `google_web_search query: "ollama-mcp-bridge config file location windows"`
Expected: Identify where the `config.json` lives for the bridge.

- [ ] **Step 3: Configure the Bridge for Local Tools**
Add `everything-search-mcp` to the bridge configuration.

---

### Task 3: High-Speed Search Integration

**Files:**
- Modify: `.ai/skills/truth-seeker/references/VERIFICATION_GUIDE.md`

- [ ] **Step 1: Verify Everything Search Tool**
Run: `uvx everything-search-mcp --help`
Expected: Tool loads and shows search commands.

- [ ] **Step 2: Perform Initial Index Scan**
Run: `uvx everything-search-mcp search "ADR"`
Expected: Near-instant results from across the workspace.

- [ ] **Step 3: Update Truth-Seeker Reference**
Add `everything-search-mcp` as the primary Tier 1 tool for internal code proof.

---

### Task 4: Dispatcher Skill Refinement (AgentSkills.io)

**Files:**
- Modify: `.ai/skills/local-orchestrator/SKILL.md`

- [ ] **Step 1: Refine Hand-Off Triggers**
Update the skill to include specific PowerShell command templates for the user to copy-paste.

- [ ] **Step 2: Implement "Return Synthesis" Logic**
Define exactly how the primary agent should parse the `<thought>` block returned by the local model.

---

### Task 5: Final Validation & Load Test

- [ ] **Step 1: Run Multi-Repo Search Audit**
Task the local agent with finding all `.csproj` files across the workspace using the bridge.
Expected: Full list returned with < 5 seconds of latency.

- [ ] **Step 2: Commit Phase 2 Completion**
```bash
git add .
git commit -m "feat: complete phase 2 local orchestration setup"
```
