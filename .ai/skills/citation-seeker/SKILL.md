---
name: citation-seeker
description: Enforces high-fidelity engineering documentation by requiring authoritative, peer-reviewed, or canonical citations for all technical claims within the Architecture of Hybrid Context Synthesis. Use before generating public documentation, specs, or blog posts.
compatibility: Requires web_fetch and google_web_search tools.
metadata:
  version: "1.1.0"
  author: Agentic Architect
---

# Citation-Seeker Skill

This skill ensures all workspace documentation is substantiated by evidence and authoritative research, supporting the Architecture of Hybrid Context Synthesis.

## Core Directives

### 1. The Substantiation Rule
You are **FORBIDDEN** from making an architectural claim without:
- **Evidence**: A link to a `verification_cmd` pass in the workspace.
- **Citation**: A link to a Tier 1 or Tier 2 authoritative source (RFC, Peer-reviewed paper, or Official SDK documentation).

### 2. Research Protocol
When searching for citations, you MUST prioritize:
1.  **RFCs & Standards** (IETF, W3C, ISO).
2.  **Official Engineering Docs** (Microsoft, Google, Anthropic).
3.  **Peer-Reviewed Research** (ACM Digital Library, IEEE Xplore, Semantic Scholar).

## Verification Logic
Every citation must be verified for "Temporal Relevance"—ensure the source reflects the 2026 state of agentic engineering.
