---
name: truth-seeker
description: Ensures all agent findings are verified via mandatory verification traces within the Architecture of Hybrid Context Synthesis. Use before updating any context files.
compatibility: Requires grep_search, glob, and web_fetch tools.
metadata:
  version: "1.2.0"
  author: Agentic Architect
---

# Truth-Seeker Skill

This skill enforces high-fidelity engineering by requiring mandatory verification traces for every fact in the Architecture of Hybrid Context Synthesis.

## Core Directives

### 1. Mandatory Research
Before proposing a change, you MUST:
- Consult global context in `/.ai/context/`.
- Consult local context in `[project]/.ai/context/`.
- Run `grep_search` to verify if documentation matches current code.

### 2. Proof of Truth Protocol
Facts are only valid if they include a **Verification Trace**:
- **Internal**: A successful terminal command (grep, build, test).
- **External**: A Tier 1 (Official) or Tier 2 (Expert) URL + excerpt.

## Detailed Procedures
See [the reference guide](references/VERIFICATION_GUIDE.md) for tiered source definitions and verification command patterns.
