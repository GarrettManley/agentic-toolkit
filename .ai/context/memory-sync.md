---
topic: Memory Sync & Cross-Agent Portability
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
status: Active
---

# Memory Sync Protocol

Standardized patterns for exporting verified facts between Gemini CLI (Home) and Claude Enterprise (Work).

## 1. The "Memory Bundle" Format
Exports must be generated as a single Markdown file containing:
- **Verified ADRs**: All accepted decisions since the last sync.
- **Project Truths**: Fragments of local context relevant to the work task.
- **Model Trace**: The reasoning path used to reach the finding.

## 2. Sync Workflow
1.  **Export**: Run `/export-memory` (Global Skill) to generate the bundle.
2.  **Ingest**: Paste the bundle into the Claude Enterprise "Project Instructions" or "System Prompt."
3.  **Validate**: The Work Agent must run a "Context Check" to confirm it has ingested the new standards.

## 3. Directionality
- **Home -> Work**: For sharing foundational engineering standards.
- **Work -> Home**: For sharing architectural findings from professional repos (scrubbed of PII).
