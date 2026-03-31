---
title: "Agent Skill: truth-seeker / SKILL.md"
date: 2026-03-30
draft: false
---

# Agent Skill: truth-seeker / SKILL.md

```text
---
name: truth-seeker
description: Ensures all agent findings are verified via empirical proof or authoritative web research before being committed to the Truth-Base. Use when the user asks to "verify," "audit," "check," or before updating any context files.
compatibility: Requires grep_search, glob, and web_fetch tools.
metadata:
  version: "1.1.0"
  author: Agentic Architect
---

# Truth-Seeker Skill

This skill enforces high-fidelity engineering by requiring evidence for every fact, forming the empirical core of the **Architecture of Hybrid Context Synthesis**.

## Core Directives

### 1. Mandatory Research
Before proposing a change, you MUST:
- Consult global context in `/.ai/context/`.
- Consult local context in `[project]/.ai/context/`.
- Run `grep_search` to verify if documentation matches current code.

### 2. Proof of Truth Protocol
Under the **Architecture of Hybrid Context Synthesis**, facts are only valid if they include **mandatory verification traces**:
- **Internal**: A successful terminal command (grep, build, test).
- **External**: A Tier 1 (Official) or Tier 2 (Expert) URL + excerpt.

## Detailed Procedures
See [the reference guide](references/VERIFICATION_GUIDE.md) for tiered source definitions and verification command patterns.

```

---
*Published from .ai active toolkit.*
