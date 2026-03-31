---
title: "Agent Skill: truth-seeker / references / VERIFICATION_GUIDE.md"
date: 2026-03-30
draft: false
---

# Agent Skill: truth-seeker / references / VERIFICATION_GUIDE.md

```text
# Verification Guide

## Tiered Source Definitions

### Tier 1: Canonical (Auto-Approval)
- Official documentation (e.g., `docs.microsoft.com`).
- Official GitHub repositories (READMEs, Wikis).
- Published RFCs or standards.

### Tier 2: Expert (Cross-Reference Preferred)
- Established engineering blogs (e.g., Netflix, AWS).
- MDN, Wikipedia (Conceptual).
- Highly-voted Stack Overflow answers.

### Tier 3: Community (Leads Only)
- Medium, Reddit, YouTube.
- **Rule**: Never commit as Truth without a Tier 1/2 corroborator.

## Verification Command Patterns
- **Directory Audit**: `dir .ai -Recurse`
- **Pattern Match**: `grep_search(pattern: "X", include_pattern: "Y")`
- **Build Pass**: `dotnet build` or `npm run build`

```

---
*Published from .ai active toolkit.*
