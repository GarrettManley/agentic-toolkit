# The Architecture of Hybrid Context Synthesis

**Status:** Active · **Version:** 1.0.0

This workspace is a hierarchical, agent-agnostic engineering environment for cost-optimized agentic orchestration. It manages multiple repositories around a centralized, verified knowledge base (the "living truth-base") so that any assistant — Gemini, Claude, or a local Ollama model — works from the same standards and facts.

## Architecture

A two-tier configuration model gives global standards with local flexibility:

- **Global truth-base (`.ai/`):** shared standards, architectural decision records (ADRs), and master persona instructions.
- **Local project context (`[project]/.ai/`):** truth files and maintenance logs unique to each repository.

## The truth-seeker protocol

To eliminate unverified "vibe coding" and hallucinations, every claim in the workspace is backed by evidence:

1. **Empirical code proof:** facts are proven via `grep`, `build`, or `test` output recorded in file metadata.
2. **Tiered authoritative web proof:**
   - Tier 1: official documentation and published RFCs.
   - Tier 2: expert engineering blogs and MDN.
   - Tier 3: community leads (investigation only).

## Tech stack

- **Orchestration:** local-first via Ollama (DeepSeek-R1) plus MCP.
- **Automation:** the Nightly Steward for scheduled context verification.
- **Runtimes:** `uv` (Python), .NET 10, Node.js 23.

## Repository guidelines

This root repository tracks the metadata and configuration of the workspace.

- **Read-only repos:** corporate and external repositories are authoritative work sources and are never modified by agentic tasks.
- **Agent autonomy:** agents may update context and skills directly but must propose code commits for manual review.
