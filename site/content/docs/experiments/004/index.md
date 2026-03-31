---
title: "Experiment 004: Surgical Replace vs. Full File Overwrite"
date: 2026-03-29
draft: false
type: "docs"
experiment_id: "004"
abstract: "This study evaluates the trade-offs between 'Surgical Replace' and 'Full File Overwrite' for modifying large files. While 'Surgical Replace' significantly reduces token costs (85% reduction), it exhibits a higher initial failure rate (40%) due to strict string matching requirements."
hypothesis: "For files over 100 lines, utilizing a surgical replace tool instead of rewriting the entire file will cut output token generation costs by 60% and reduce syntax hallucination."
methodology:
  model: "Gemini 2.0 Flash"
  temperature: 0.1
  n_trials: 10
  system_prompt: "Comparing 'Full Overwrite' (write_file) vs. 'Surgical Replace' (replace) strategies."
---

## 1. Introduction
Rewriting entire large files to make small edits is expensive and error-prone. This experiment explores if a surgical approach can maintain high performance while reducing costs.

## 2. Methodology
The experimental setup involved updating a variable deeply nested in a 500-line mock file. We compared 'Full Overwrite' (rewriting the entire file) against 'Surgical Replace' (using exact string matching for targeted updates).

## 3. Results
{{< experiment-metrics id="004" >}}

The study confirms that while `replace` is significantly cheaper in terms of output tokens, it has a much higher failure rate due to line ending mismatches (CRLF vs LF) and strict matching requirements. It requires more careful tool usage but is the only sustainable way to edit large files.

## 4. Discussion & Limitations
The higher failure rate of `replace` (60% initial success) is primarily due to regex and matching rigor. To improve this, pre-processing line endings and providing more context in the search string are recommended. A file-size heuristic should determine when to switch from `write_file` to `replace`.

## 5. Reproducibility
Verified by Garrett Manley on 2026-03-29.
