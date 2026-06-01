# Posture and Productization Plan

**Tracker:** hb-doc.2 · **Status:** Completed (historical, 2026-03) · **Phase:** 4

> For agentic workers: use `superpowers:subagent-driven-development` (preferred) or `superpowers:executing-plans` to run this plan task-by-task.

## Goal and value

Convert the workspace's agentic traces and ADRs into professional technical capital (case studies and a portable SDK) that positions the author as a leader in agentic engineering. The value is reusable, shippable proof of the workflow.

## Approach

A content-extraction layer that summarizes technical decision loops into human-readable case studies, plus a packaging layer that makes the `.ai/` structure portable.

- Static site engine: Hugo (standard for the personal site).
- Extraction: Python (agent-assisted).
- Formatting: GitHub-flavored Markdown.

## Ordered steps

### Task 1: The agentic-trace extractor

Create `.ai/scripts/extract_case_study.py`; modify `.ai/adr/001-workspace-foundation.md`.

- [x] Add `trace_id` metadata to the ADR template, linking each decision to its originating session.
- [x] Build an extractor that reads an ADR and its morning briefing to generate a "vibe vs. veracity" case study.

### Task 2: Blog integration

Create a launch blog post and `.ai/templates/blog-post-template.md`.

- [x] Create a blog-export skill that writes technical content in Garrett's voice (direct, technical, authoritative).
- [x] Map `.ai/` metadata (`source_tier`, `last_verified`) into Hugo frontmatter for SEO and authority.

### Task 3: The agentic-SDK manifest

Create `ai-workspace-manifest.json` and `.ai/scripts/bootstrap_project.ps1`.

- [x] Define a JSON manifest listing the global skills and context files a best-in-class workspace needs.
- [x] Build a project injector that drops the hierarchical agentic infrastructure into any local directory.

### Task 4: KPI and value vetting

Create `.ai/context/maintenance/kpi-tracking.md`.

- [x] Define 2026 success metrics: cost savings (local vs. metered tokens), knowledge density (Tier 1 facts per project), and zero-drift compliance (days since last unhandled drift).

### Task 5: Global self-audit

- [x] Run the full steward-to-blog loop and produce a status-report post.
- [x] **Step 2: Final Workspace Repo Push** — *historical; completed 2026-03. Original command preserved verbatim (this 2026-06 standardization pass commits centrally and never `git add -A`):*

```bash
git add .
git commit -m "feat: complete phase 4 productization and launch readiness"
```

## Retrospective

Updates hb-doc.2.

Outcome: implemented in 2026-03. `.ai/scripts/extract_case_study.py`, `.ai/scripts/package_sdk.py`, `.ai/scripts/bootstrap_project.ps1`, and `ai-workspace-manifest.json` all exist. The manifest name is "The Architecture of Hybrid Context Synthesis", consistent with the rebranding. The original git-commit step is recorded as completed; commits are handled centrally. Retained as a historical record.
