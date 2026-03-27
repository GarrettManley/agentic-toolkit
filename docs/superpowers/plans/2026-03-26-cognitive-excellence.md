# Phase 5: Cognitive Balancing & Qualitative Excellence

> **Goal:** Eliminate "Agent-Cluster Vibe" by rebalancing tasks between Cloud and Local tiers, ensuring high-fidelity prose and authoritative synthesis.

## 1. The Intelligence Tiering Protocol (ITP)
We will refactor our orchestration scripts to follow a strict delegation matrix:

| Task Category | Tier | Primary Model |
| :--- | :--- | :--- |
| **Strategy & Planning** | Cloud (Reasoning) | Gemini 2.0 Pro |
| **Prose & Public Content** | Cloud (Creative) | Gemini 2.0 Pro |
| **Research Synthesis** | Cloud (Knowledge) | Gemini 2.0 Flash |
| **Tool Execution/Shell** | Local (Tooling) | Qwen 2.5 Coder 7B |
| **Static Code Audit** | Local (Verification) | DeepSeek-R1 8B |

---

## 2. Qualitative Refinement Loop
We will replace the "Infinite Local Loop" with a "Cloud-Synthesis" pass.

- [ ] **Task 5.1: Refactor `refine_content.py`**
  - Use **Gemini 2.0 Pro** for the final content synthesis.
  - Command: "Synthesize these 8 persona critiques into a single, cohesive human voice (Garrett Manley)."
  - Constraint: Prevent "The model said..." or "The auditor found..." meta-talk.

- [ ] **Task 5.2: Qualitative Analysis Framework**
  - Implement a `score_voice.py` script using Gemini to grade content on:
    - **Authority**: Does it sound like a Senior Architect?
    - **Cohesion**: Does it flow naturally without repetition?
    - **Directness**: Does it avoid "Agent-isms" (e.g., "In conclusion," "It is important to note").

---

## 3. High-Fidelity Content Re-Launch
We will re-author the current site content to kill the "cluster vibe."

- [ ] **Step 1: Homepage Rewrite**
  - Re-synthesize the "Architect's Laboratory" prose using Cloud reasoning.
- [ ] **Step 2: ADR Consolidation**
  - Merge fragmented ADR critiques into authoritative technical specifications.

---

## 4. Cost-Performance Monitoring
- [ ] **Task 5.3: Update Telemetry**
  - Track **"Cloud-to-Local Ratio"** alongside T-CER.
  - Define the "Sweet Spot" where quality is maximized while costs remain <$1.00 per session.
