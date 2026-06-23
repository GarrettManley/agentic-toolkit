# Retrospective: sec-research Stage 5 (Triage & Dedup) + Stage 6 (Report Drafting)

**Plan:** `~/.claude/plans/writing-plans-brainstorming-workflows-l-sorted-token.md`
**Commit:** `12a2829` (`fix(stage6): final-review cleanups (dead code, CVSS prefix strip, advisory key, dedup comment)`)
**Date:** 2026-06-23

## Outcome

Closed the sec-research pipeline's "last mile." The toolset now runs end-to-end — `recon → hypothesize → verify → triage → draft` — converting verified verdicts into deduplicated, schema-valid finding documents instead of stopping at `verdicts.json`. Stage 5 (`scripts/triage/`) dedups verified verdicts against the OSV advisories recon already fetched (CVE-equality match → `duplicate`/dropped, else `novel`); Stage 6 (`scripts/draft/`) runs novel verdicts through a deterministic `FINDING_TEMPLATE_REGISTRY`, allocates a `FIND-YYYY-MM-DD-NNN` trace-id, self-validates (schema + PoT-2 evidence discipline), and writes `findings/<trace-id>/`. LLM prose is a closed seam. 12 tasks, subagent-driven; test suite 116 → 344 passing (+228), green at every commit and on the merged result. Merged to master (fast-forward); beads `hb-4kd`/`hb-57f` closed, `hb-yz5` filed for follow-ups.

## What worked

- **Subagent-driven with model tiering** — haiku for verbatim-code transcription tasks (1, 2, 6), sonnet for integration/schema judgment (3, 5, 8–12), opus for the final whole-branch review. Matched cost to task difficulty without quality loss.
- **Per-task adversarial reviewer with named-risk prompts** — naming the specific cross-task risk to scrutinize (e.g. "does the EvidenceCapture reconstruction survive to Stage 6 attribute access?") caught every integration bug at the task boundary, before it compounded.
- **"Confirm X first" brief notes** — delegating the reality-check (recon's real on-disk shape, the real `finding.schema.json` keys, the ledger helper signature) to implementers who read the actual code, rather than trusting the plan's guesses, paid off repeatedly. The plan's guessed values were wrong in three places; implementers caught all three because the brief told them the schema/code was canonical.
- **File handoffs (briefs / reports / review-package diffs)** kept the controller's context clean across 12 tasks + ~30 subagent dispatches.
- **Final review on opus verifying the FULL live jsonschema** (not just the in-house self-validator) confirmed auto-drafts are born compliant and won't be rejected on later human edit — the load-bearing correctness result.

## Friction / bugs

- **stage_verify dict boundary dropped nested dataclasses**
  - *What happened:* Task 5 reconstructed `Verdict` from the `asdict()`-flattened dicts `stage_verify` returns, but left `evidence` as `list[dict]`. Stage 6's template reads `evidence[i].exit_code` via attribute access — it would have crashed in the real pipeline (unit tests used `evidence=[]`, so they passed).
  - *Root cause:* `asdict()` recursively flattens nested dataclasses; a top-level `Verdict(**dict)` reconstruction does not rebuild them.
  - *How caught:* Task 5 reviewer's named-risk scrutiny (the controller flagged it pre-review from the implementer's report).
  - *Fix:* `_verdict_from_dict` rebuilds each `EvidenceCapture(**e)`; a test asserts `isinstance(evidence[0], EvidenceCapture)`.
  - *Rule:* When a boundary serializes via `asdict()`, any downstream reconstruction must rebuild nested dataclasses, and a test must assert `isinstance` on the nested type — not just the top-level object.

- **Plan briefs guessed schema field names**
  - *What happened:* Task 8/9 briefs invented `deduplication_check.checked_against` as a CVE-id list and put semantic fields in `evidence`; the real `finding.schema.json` has `checked_against` as an enum `[nvd,ghsa,osv]` and a closed (`additionalProperties:false`) `evidence` triplet.
  - *Root cause:* Writing template-output specs from memory instead of reading the schema first.
  - *How caught:* Implementers were instructed to treat the schema file as canonical; they read it and overrode the brief.
  - *Fix:* Followed the real schema; semantic data moved to body/citations.
  - *Rule:* For schema-bound output, the brief must label its field names "provisional — the schema file governs," and point the implementer at the schema as step one. (This worked — generalize it to every schema-bound task.)

- **Test wrote the real ledger**
  - *What happened:* A Task 4 test exercised `persist_triage` without patching the ledger, appending to the real `submissions/ledger.jsonl`. The report's "ledger stayed clean" claim was true only because other tests in the file happened to patch it.
  - *Root cause:* Per-test isolation not enforced; a global "clean after the run" check masks per-test leaks.
  - *How caught:* Task 4 reviewer.
  - *Fix:* `monkeypatch` the ledger in every test that triggers an append.
  - *Rule:* Every test exercising a ledger-appending function must patch the ledger; verify the real ledger is untouched per-test, not just once at the end.

- **Circular import between registry and its registered template**
  - *What happened:* `registry.py` imports the template factory; the template needs `IncompleteVerdict`, which the plan placed in `registry.py` — a cycle.
  - *Root cause:* Shared exception co-located with the module that imports the things that raise it.
  - *How caught:* Pre-flight plan scan (before any dispatch).
  - *Fix:* `IncompleteVerdict` in a leaf `errors.py`, re-exported from `registry`; executed the template task (8) before the registry task (7).
  - *Rule:* Put shared exceptions in a leaf module; pre-flight-scan registry/plugin patterns for cycles and order tasks leaf-first.

- **Scoped npm package parse + CVSS charset-strip**
  - *What happened:* `partition("@")` rejected `@scope/pkg@1.0.0`; `lstrip("CVSS:3.1/")` is a character-set strip, not a prefix strip.
  - *Root cause:* String-method misuse (both are easy to reach for and wrong here).
  - *How caught:* `partition` bug by Task 8 reviewer; `lstrip` by the final opus review.
  - *Fix:* `rpartition("@")`; `removeprefix("CVSS:3.1/")` (with a guarding test).
  - *Rule:* `pkg@version` → `rpartition` (scoped names start with `@`); never `lstrip`/`rstrip` for literal prefixes/suffixes — use `removeprefix`/`removesuffix`.

## Concrete improvements

- **Brief convention: mark provisional values** — when a brief contains field names/paths the plan author didn't verify against the code, label them provisional and name the canonical source file. Done for this plan's schema/recon/ledger tasks; worth making a standing brief-writing habit.
- **Nested-dataclass reconstruction test** — `isinstance` assertion on rebuilt nested types is now in `test_nightly_stage5_6.py`; reusable pattern for any `asdict()` boundary.
- **Follow-ups tracked in `hb-yz5`** — self-validator is a weaker proxy than the live jsonschema gate on the `deterministic`-without-hash edge (unreachable today); a validate.py test gap; and running `VERIFY_LIVE=1` e2e on a WSL2 docker host (shares the docker dependency with `hb-ctr`).
