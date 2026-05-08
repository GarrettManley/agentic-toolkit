# Playbook Format

Playbooks are the workspace's persistent learning substrate. Two layers:

## Class playbooks (`playbooks/<vuln-class>/<technique>.md`)

One per `(vuln-class, technique)` pair. Loaded into hypothesis-generation context (Stage 4) scoped to relevant classes for the program being investigated.

### Required sections

```markdown
# <Vuln Class> — <Technique Name>

**Trace ID**: trace-pb-YYYY-MM-DD-NNN
**Last updated**: YYYY-MM-DD (cite source finding trace-id if updated from accepted/rejected report)

## When to look for this
Concrete signals in scope or recon output that suggest this technique is worth attempting.

## Signal patterns (positive indicators)
Bulleted list of patterns that increase confidence this technique applies.

## False-positive patterns (negative indicators)
Bulleted list of patterns that look promising but are usually false positives.

## Evidence template
The exact fields/artifacts a finding for this technique must produce. Tied to `schema/evidence.schema.json`.

## Dedup heuristics
How to check if this finding is a known dupe before drafting the report. Tied to `deduplication_check{}` schema.

## Citations
- [1] Tier-1 source for the technique (paper/RFC/canonical writeup)
- [2] Optional Tier-2 corroborator
```

### Example: `playbooks/dependency-cve/postinstall-exec-injection.md`

(Will be authored as Stage 4 produces real findings — Stage 1 ships only the directory structure.)

## Meta playbooks (`playbooks/_meta/`)

Three files, all start empty and grow over time:

### `accepted-patterns.md`
Distilled lessons from accepted reports. Sections per vuln-class. Cite source finding trace-ids.

### `rejected-patterns.md`
Distilled rejection signals — especially anti-AI-slop signals from venues. Examples:
- "Curl maintainers reject reports that claim 'the parser might be vulnerable to X' without a working PoC"
- "huntr rejects findings where `affected_versions_range` is overly broad"
- "GHSA closes reports that don't include `vulnerable_function_path`"

### `dedup-pitfalls.md`
Dupes hit and how to catch them earlier. Each entry: trace-id of the finding that turned out to be a dupe, the source it dupes against, the dedup-check method that would have caught it.

## The feedback loop (Stage 7 maturation; Stage 1 ships substrate only)

When a finding's `status` transitions to `accepted` / `rejected` / `duplicate`:

1. PostToolUse hook appends entry to `runtime/feedback-queue.jsonl`
2. (Stage 7) Next nightly run reads the queue and asks Claude to:
   - Read each feedback entry's finding
   - Identify what about the relevant playbook would have improved this outcome
   - Draft a playbook update as a commit
3. The proposed playbook commit is hard-blocked at G-1 unless it includes reasoning + at least one Trace-ID citation back to the source finding
4. Researcher reviews the playbook diff, merges or rejects

## Stage 1 ships

- The directory structure (`playbooks/_meta/` + `playbooks/<class>/` placeholders)
- The `runtime/feedback-queue.jsonl` writer in PostToolUse
- This format documentation

## Stage 7 ships

- The playbook-update generation logic
- Class-scoped playbook loading in nightly's hypothesis-generation step
