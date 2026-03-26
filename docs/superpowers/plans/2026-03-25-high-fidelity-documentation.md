# Phase 4: Technical Documentation & Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform workspace reasoning traces into full, complete engineering documentation for `garrettmanley.dev`, substantiated by documented execution evidence and peer-reviewed citations.

**Architecture:** A "High-Fidelity Publisher" loop that connects local agentic findings to external authoritative research, outputting structured documentation via Firebase.

**Tech Stack:**
- **Static Site Engine**: Hugo (Documentation-centric theme)
- **Citations**: Semantic Scholar API / IEEE / W3C / Official Docs
- **Hosting**: Firebase (Classic + App Hosting)

---

### Task 1: The "Citation-Seeker" Skill

**Files:**
- Create: `ai/skills/citation-seeker/SKILL.md`
- Create: `ai/skills/citation-seeker/references/CITATION_STANDARDS.md`

- [ ] **Step 1: Define Authoritative Citation Logic**
Create a skill that forces agents to find a Tier 1 (Canonical) or peer-reviewed citation for every major architectural statement.

- [ ] **Step 2: Automate Research Hook**
Write a Python script that uses `google_web_search` specifically targeting `.edu`, `.org`, and official documentation sites to retrieve citations.

---

### Task 2: The Evidence-Based Spec Generator

**Files:**
- Create: `.ai/scripts/generate_spec.py`
- Create: `.ai/templates/engineering-spec.md`

- [ ] **Step 1: Implement Evidence Injection**
The generator must extract the `evidence` field from our Truth Files and the raw CLI output from `steward.py` logs to "Prove" the documentation.

- [ ] **Step 2: Build the Spec Template**
Define a template that includes "Verification Trace," "Hardware Context," and "Peer-Reviewed References" sections.

---

### Task 3: Firebase Documentation Hub (`garrettmanley.dev`)

**Files:**
- Create: `ai/context/infrastructure/dev-site-architecture.md`
- Create: `firebase.json` (Root update)

- [ ] **Step 1: Initialize Hugo for Documentation**
Setup a documentation-centric Hugo project in a `site/` directory (ignored by work-repos).

- [ ] **Step 2: Direct-to-Firebase Pipeline**
Use the Firebase CLI to automate the push from `generate_spec.py` -> `hugo build` -> `firebase deploy`.

---

### Task 4: The "Agentic SDK" Packaging

**Files:**
- Create: `ai-workspace-manifest.json`
- Create: `.ai/scripts/package_sdk.py`

- [ ] **Step 1: Standardize the Metadata Schema**
Ensure all context and skill files follow a versioned, machine-readable schema for the SDK.

---

### Task 5: Launch Audit (The "Veracity Check")

- [ ] **Step 1: Run Final Substantiated Audit**
Perform an audit where every finding must have a linked citation. 

- [ ] **Step 2: Final Workspace Repo Push**
```bash
git add .
git commit -m "feat: complete phase 4 high-fidelity documentation architecture"
```
