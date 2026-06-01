# High-Fidelity Documentation and Productization Plan

**Tracker:** hb-doc.2 · **Status:** Completed (historical, 2026-03) · **Phase:** 4

> For agentic workers: use `superpowers:subagent-driven-development` (preferred) or `superpowers:executing-plans` to run this plan task-by-task.

## Goal and value

Turn workspace reasoning traces into complete engineering documentation for the public lab site, substantiated by recorded execution evidence and peer-reviewed citations. The value is publishable, defensible technical capital instead of unverifiable summaries.

## Approach

A high-fidelity publisher loop that links local agentic findings to external authoritative research and outputs structured documentation through Firebase.

- Static site engine: Hugo (documentation-centric theme).
- Citations: Semantic Scholar API, IEEE, W3C, official docs.
- Hosting: Firebase.

## Ordered steps

### Task 1: The citation-seeker skill

Create `.ai/skills/citation-seeker/SKILL.md` and a citation-standards reference.

- [x] Define authoritative citation logic that requires a Tier 1 (canonical) or peer-reviewed citation for every major architectural statement.
- [x] Automate a research hook that targets `.edu`, `.org`, and official documentation sites.

### Task 2: The evidence-based spec generator

Create `.ai/scripts/generate_spec.py` and `.ai/templates/engineering-spec.md`.

- [x] Implement evidence injection that extracts the `evidence` field from truth files and raw CLI output from steward logs.
- [x] Build a spec template with "Verification Trace", "Hardware Context", and "Peer-Reviewed References" sections.

### Task 3: Firebase documentation hub

Create the dev-site architecture context and a root `firebase.json`.

- [x] Initialize a documentation-centric Hugo project in `site/`.
- [x] Wire the direct-to-Firebase pipeline: `generate_spec.py` to `hugo build` to `firebase deploy`.

### Task 4: Agentic SDK packaging

Create `ai-workspace-manifest.json` and `.ai/scripts/package_sdk.py`.

- [x] Standardize a versioned, machine-readable metadata schema for context and skill files.

### Task 5: Launch audit (veracity check)

- [x] Run a final audit where every finding carries a linked citation.
- [x] **Step 2: Final Workspace Repo Push** — *historical; completed 2026-03. Original command preserved verbatim (this 2026-06 standardization pass commits centrally and never `git add -A`):*

```bash
git add .
git commit -m "feat: complete phase 4 high-fidelity documentation architecture"
```

## Retrospective

Updates hb-doc.2.

Outcome: implemented in 2026-03. The `citation-seeker` skill (`.ai/skills/citation-seeker/`), `.ai/scripts/generate_spec.py`, `.ai/scripts/package_sdk.py`, and `ai-workspace-manifest.json` all exist. The site deploys via Firebase. The original Task 5 step 2 embedded a raw `git add . && git commit`; commits are now handled centrally and scoped, so that step is recorded as completed rather than re-runnable here. Retained as a historical record.
