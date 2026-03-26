# Phase 4: Posture & Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the workspace's internal "Agentic Traces" and ADRs into professional technical capital (blog posts and a portable SDK) to posture the user as a leader in Agentic Engineering.

**Architecture:** A "Content Extraction" layer that summarizes technical decision loops into human-readable case studies, combined with a "Packaging" layer that makes the .ai/ structure portable.

**Tech Stack:**
- **Static Site Engine**: Hugo/Jekyll (Standard for garrettmanley.com)
- **Extraction**: Python (Agent-assisted)
- **Formatting**: GitHub Flavored Markdown (Blog ready)

---

### Task 1: The "Agentic Trace" Extractor

**Files:**
- Create: `.ai/scripts/extract_case_study.py`
- Modify: `.ai/adr/001-workspace-foundation.md`

- [ ] **Step 1: Implement "Trace" Metadata**
Update the ADR template to include a `trace_id`—a machine-readable link to the specific session where the decision was made.

- [ ] **Step 2: Build the Extractor Script**
Write a Python script that reads an ADR and its corresponding Morning Briefing to generate a "Vibe vs. Veracity" case study.
*Example Content*: "The Agent identified drift in X, used Tool Y to verify, and implemented Fix Z at zero metered cost."

---

### Task 2: Hugo/Jekyll Blog Integration

**Files:**
- Create: `docs/superpowers/blog/YYYY-MM-DD-workspace-launch.md`
- Create: `.ai/templates/blog-post-template.md`

- [ ] **Step 1: Create Blog Export Skill**
A new skill `ai/skills/blog-generator` that tells agents how to write technical content in "Garrett's Voice" (Direct, Technical, Authoritative).

- [ ] **Step 2: Automate Frontmatter Mapping**
Ensure the export script maps `.ai/` metadata (source_tier, last_verified) into Hugo/Jekyll tags for SEO and authority.

---

### Task 3: The "Agentic SDK" Manifest

**Files:**
- Create: `ai-workspace-manifest.json`
- Create: `.ai/scripts/bootstrap_project.ps1`

- [ ] **Step 1: Define the Workspace Blueprint**
Create a JSON manifest that lists all required global skills and context files for a "Best-in-Class" workspace.

- [ ] **Step 2: Build the "Project Injector"**
A PowerShell script that allows you to point to any local directory and "Drop" the hierarchical agentic infrastructure into it instantly.

---

### Task 4: KPI & Value Vetting (The Dogfooding Dashboard)

**Files:**
- Create: `.ai/context/maintenance/kpi-tracking.md`

- [ ] **Step 1: Define 2026 Success Metrics**
*Metric 1*: **Cost Savings** (Number of local reasoning tokens vs. metered equivalent).
*Metric 2*: **Knowledge Density** (Number of Tier 1 verified facts per project).
*Metric 3*: **Zero-Drift Compliance** (Days since last unhandled technical drift).

---

### Task 5: Final Global Self-Audit

- [ ] **Step 1: Run Full "Steward to Blog" Loop**
Task the Steward with auditing the workspace, then task the Blog-Generator with writing a "Status Report" post about it.

- [ ] **Step 2: Final Workspace Repo Push**
```bash
git add .
git commit -m "feat: complete phase 4 productization and launch readiness"
```
