# Engineering Specification: Academic Research Dashboard (Hugo/Hextra)

**Standard:** IEEE 830-1998 (Software Requirements) | **Trace ID:** trace-20260330-001
**Status:** DRAFT | **Author:** Gemini CLI | **Date:** 2026-03-30

---

## 1. Objective
Transform the `site/` Hugo-based lab website into a formal **Computer Science Research Portal**. This includes moving from "informationally sparse" summaries to rigorous, data-driven academic documentation for all workspace experiments.

## 2. Academic Content Structure (IMRAD)
All experiment Markdown files in `site/content/docs/experiments/` will be refactored to follow a formal academic structure:
- **Abstract:** 150-250 words summarizing the problem, intervention, and results.
- **Introduction:** Defines the "Agentic Gap" and the specific hypothesis.
- **Methodology:** Detailed experiment setup (Models, temperature, N-size, prompts).
- **Results:** Quantitative analysis with high-density metrics (CPS, Pass^k, Efficiency).
- **Discussion & Limitations:** Analysis of why results occurred and identification of biases.
- **Reproducibility:** Machine-readable Trace IDs and commands for verification.

## 3. Data-Driven Architecture
Transition quantitative metrics into a structured **Experiment Data Layer** to ensure consistency and automation:
- **Experiment Folders:** Each experiment will have its own directory containing a `data.json` or `metrics.yaml` file (e.g., `site/content/docs/experiments/001/data.json`).
- **Raw Metric Storage:** These data files will store raw counts (successes, trials, tokens) rather than pre-calculated percentages.
- **Hugo Shortcodes:** Custom shortcodes (e.g., `{{< experiment-metrics id="001" >}}`) will calculate Pass^k, CPS, and Token-per-Success on-the-fly at build-time.
- **Visualization:** Integration of SVG or Chart.js based rendering for "Confidence Intervals" and "Performance Trends."

## 4. Visual Layout & Dashboard
Enhance the **Hextra** theme for a scientific aesthetic and centralized metrics tracking:
- **Global Research Dashboard:** A single-page view aggregating all experiment scorecard data from the JSON files.
- **Layout Toggles:** Toggle between "Executive View" (high-level) and "Research View" (full academic rigor).
- **Workspace Pulse Chart:** A global trendline on the homepage showing the reduction in CPS and increase in Pass^k over time.
- **Callout Components:** Professional-grade UI components for "Hypothesis Blocks," "Observations," and "Data Tables."

## 5. Success Criteria
- [ ] Zero instances of "informationally sparse" descriptions in validated experiments.
- [ ] Build-time calculation of all primary metrics (no manual math in Markdown).
- [ ] Automated aggregation of results into the Global Dashboard.
- [ ] Verified rendering of data visualizations in the published HTML.

## 6. Implementation Stages
1. **Stage 1: Core Templates:** Create the IMRAD archetypes and shortcodes.
2. **Stage 2: Data Migration:** Move existing metrics from 001-005 into `data.json` files.
3. **Stage 3: Dashboard Build:** Implement the global aggregation logic and layout toggles.
4. **Stage 4: Visual Polish:** Finalize the "Scientific Lab" aesthetic.

---
*Verified by Gemini CLI on 2026-03-30.*
