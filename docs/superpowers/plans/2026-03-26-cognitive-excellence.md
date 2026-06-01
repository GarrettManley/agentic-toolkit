# Cognitive Balancing and Qualitative Excellence Plan

**Tracker:** hb-doc.2 · **Status:** Completed (historical, 2026-03) · **Phase:** 5

## Goal and value

Remove the "agent-cluster" texture from generated content by rebalancing tasks across cloud and local tiers, producing high-fidelity prose and authoritative synthesis. The value is content that reads as a single senior-architect voice rather than stitched-together model output.

## Approach

Adopt a strict delegation matrix and replace the infinite local refinement loop with a single cloud-synthesis pass.

## Ordered steps

### Task 1: Intelligence tiering protocol

Refactor the orchestration scripts to follow a fixed delegation matrix.

| Task category | Tier | Primary model |
| :--- | :--- | :--- |
| Strategy and planning | Cloud (reasoning) | Gemini 2.0 Pro |
| Prose and public content | Cloud (creative) | Gemini 2.0 Pro |
| Research synthesis | Cloud (knowledge) | Gemini 2.0 Flash |
| Tool execution and shell | Local (tooling) | Qwen 2.5 Coder 7B |
| Static code audit | Local (verification) | DeepSeek-R1 8B |

### Task 2: Qualitative refinement loop

- [x] Refactor `refine_content.py` to use a cloud model for final synthesis, merging persona critiques into one cohesive voice and preventing "the model said" meta-talk.
- [x] Implement `score_voice.py` to grade content on authority, cohesion, and directness (avoiding agent-isms such as "in conclusion" or "it is important to note").

### Task 3: High-fidelity content re-launch

- [x] Rewrite the homepage prose using cloud reasoning.
- [x] Consolidate fragmented ADR critiques into authoritative technical specifications.

### Task 4: Cost-performance monitoring

- [x] Track the cloud-to-local ratio alongside the token-cost-efficiency rate, and define the sweet spot where quality is maximized while cost stays under roughly one dollar per session.

## Retrospective

Updates hb-doc.2.

Outcome: implemented in 2026-03. `.ai/scripts/refine_content.py` and `.ai/scripts/score_voice.py` both exist. The model names in the tiering matrix reflect the cloud tier as configured at the time and are recorded as historical; the local tier (Qwen 2.5 Coder, DeepSeek-R1 8B) still matches the current hardware strategy. Retained as a historical record.
