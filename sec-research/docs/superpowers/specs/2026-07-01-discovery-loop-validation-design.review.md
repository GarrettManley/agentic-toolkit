# Adversarial Design Review — Discovery-Loop Validation & Stage 7 (huntr) Wiring

**Design reviewed:** `docs/superpowers/specs/2026-07-01-discovery-loop-validation-design.md`
(this review was run against the *initial draft* of that design, before revision; the
committed design doc already incorporates every resolution below)
**Date:** 2026-07-01
**Agents:** 4 independent parallel reviewers — `docs:plan-skeptic`,
`docs:plan-feasibility-auditor`, `docs:plan-scope-cutter`, and a general-purpose
security-lens reviewer, each blind to the others' findings, each instructed to verify
every factual claim directly against the repo rather than trust the design summary handed
to it.
**Verdict: material rework required.** The initial draft's step "novel discovery" goal was
architecturally unreachable, its "revalidation" step targeted the wrong root cause, and a
pre-existing PT-2 bypass would have had its blast radius substantially widened by the
initial Stage 7 scope. All four are resolved in the committed design.

---

## CRITICAL

```
[CRITICAL] (feasibility-auditor) — the initial design's step 3 ("prove the unproven
novel-discovery capability") is unreachable by the current pipeline for the only
implemented vuln class. select_playbooks (llm/playbook.py) gates dependency-cve entirely
on recon_item["known_advisories"] being non-empty; the system prompt (llm/prompt.py)
explicitly forbids inventing a CVE outside that list; triage's dedup check
(triage/dedup.py + triage/recon_advisories.py) runs against the EXACT SAME advisory list
the hypothesis was seeded from. A successful verify->triage cycle can therefore only ever
land on TRIAGE_DUPLICATE or a null — never TRIAGE_NOVEL.
  RESOLUTION: step reframed to an explicitly honest, reachable goal — "prove the pipeline
  behaves correctly end-to-end against a fresh target," with TRIAGE_DUPLICATE or a
  defensible null as the only stated success criteria. Novel discovery moved to Non-goals
  (§1.4) with the mechanism gap named explicitly (an unrestricted hypothesis-gen mode +
  a triage rule distinguishing "reachable despite a claimed fix" from a true duplicate —
  a separate, larger feature, not attempted here).

[CRITICAL] (plan-skeptic, independently verified by the orchestrating session) — the
initial design's revalidation step targeted the wrong root cause and the wrong prior run.
hb-322 fetched minimatch via the HUNTR fetcher, not GHSA — hb-7hf's own plan doc states
this explicitly ("hb-322 ... fetched minimatch via the huntr fetcher ... which already
emits package-typed assets ... and never touches this code path"). The 0-hypotheses
outcome was a genuine correct model decision (all 9 correlated advisories targeted
transitive, not direct, dependencies) — confirmed via a ledger query showing zero
silent-drop-path entries — not a bug hb-7hf fixed. Re-running minimatch would almost
certainly reproduce the identical (correct) null and validate nothing new; the actual
open question ("does claude-cli reliably author discriminating PoCs") was never exercised
by that run, since 0 hypotheses means verify/PoC-authoring never got invoked.
  RESOLUTION: revalidation step replaced entirely with scripts/eval/authoring_eval.py
  --track b (independently confirmed to exist, be provider-agnostic via the existing
  SECRESEARCH_LLM_PROVIDER, and score against a real differential oracle over N trials
  using the same fixture that already disqualified qwen2.5-coder-7b). This directly and
  cheaply answers the actual open question, with no live venue fetch and no dependency on
  a real program happening to be vulnerable. See design §2.1.

[CRITICAL] (security-lens reviewer, independently verified by the orchestrating session
via direct source read) — sign_approval.py / sign_override.py both define an unconditional
--test-mode-confirm flag (confirmed at sign_approval.py:133-134: `if
args.test_mode_confirm: confirmed = True`) with zero hook coverage anywhere (grep across
all four hook files confirms no rule matches invocations of either script — only
suggested override_path strings). A token minted this way is bit-for-bit indistinguishable
from a genuine human-approved one; PT-2 validates signature/expiry/trace/venue match only,
never provenance. Pre-existing, but the initial design's Stage 7 scope (a live, opaque
POST to api.hackerone.com/v1 with no human in the loop) would have raised this bug's blast
radius from low (today: manual-form requires a physical human paste; gh api produces a
reviewable draft) to unbounded.
  RESOLUTION: closing this bypass is now a stated blocking prerequisite (design §3) before
  any Stage 7 dispatch work proceeds — not deferred, not a "nice to have." Stage 7 scope
  itself was also narrowed (see IMPORTANT, below) independently reducing residual exposure
  even after the fix lands.
```

## IMPORTANT

```
[IMPORTANT] (security-lens reviewer, independently verified) — unattended nightly cron
(sec-research-nightly, already registered, daily 3am) has no supervision-persistence
mechanism. run_unattended() and run_supervised() call the identical stage functions; no
unload/archive/deactivate mechanism exists anywhere in scripts/ or hooks/lib/, and the
scope schema has no supervised-only/paused/TTL field. Once a fresh scope is loaded, every
subsequent unattended run reprocesses it to full draft-finding completion with zero human
checkpoint, and (once PoC-authoring is pinned to a real provider) makes live, unsupervised
API calls authoring and executing exploit code, unbounded.
  RESOLUTION: added as a new, previously-absent, mandatory design component (§2.3,
  "scope-lifecycle control") — not optional, blocks step 2 from loading its target until
  one of unload-after-session / a supervised-only schema flag / a TTL gate is chosen and
  built.

[IMPORTANT] (security-lens reviewer, independently verified via direct source read at
submit.py:344) — the initial design's "alias huntr to manual-form" approach has a real
status-mislabeling bug: `new_status = "submitted-manual" if args.venue == "manual-form"
else "submitted"` is keyed on the venue STRING, not on which dispatch function actually
ran. Aliasing huntr into a new elif branch while keeping venue="huntr" (as the initial
design proposed) falls to the else branch and stamps a false, fully-confirmed "submitted"
status — even though only a browser-open + clipboard-copy occurred, with no way to verify
the human actually completed the paste.
  RESOLUTION: design §2.4 now states the fix explicitly as a required part of step 3 —
  derive new_status/outcome from which dispatch function ran (or an explicit
  confirmed-by-human bit), not from the venue string.

[IMPORTANT] (scope-cutter + feasibility-auditor, convergent) — real ibb-h1 submission
automation in this same arc is premature: (a) speculative against an outcome now proven
unreachable in the novel sense and uncertain even in the defensible-null sense (step 2 may
not even target an IBB-scoped program); (b) the read-path payload shape
(scripts/fetchers/ibb.py) is self-flagged by its own docstring as an unreconciled
assumption never verified against a live account; (c) it is unverified whether
api.hackerone.com/v1 exposes any report-creation endpoint for researcher accounts at all
(historically web-form-driven) — if not, the entire "ibb-h1 integration" collapses to
"alias to manual-form" (cheap) rather than a new POST integration (not cheap), a large
unbudgeted swing.
  RESOLUTION: ibb-h1 moved to Non-goals (§1.4), deferred to a future arc gated on an
  actual finding that needs it.

[IMPORTANT] (scope-cutter) — direct-maintainer's inclusion was speculative on its face:
the initial design's own language admitted its exact shape was unknown until step 2 (then
step 3) produced a concrete target to disclose to.
  RESOLUTION: moved to Non-goals (§1.4) alongside ibb-h1, for the same reason — not
  plannable without a concrete target.

[IMPORTANT] (security-lens reviewer) — the initial design's instruction to build ibb-h1
"mirroring the ghsa dispatcher's pattern" would have carried forward an unsafe habit:
ghsa's verbose print/ledger-note logging is safe only because gh auth hides credentials
invisibly; ibb-h1 needs a literal Basic-Auth header built from a keyring token, and naive
logging-pattern reuse risks leaking it into stdout (persisted via run_nightly.ps1 + S-2
session transcripts) or into submissions/ledger.jsonl's notes field on a failure path —
confirmed that file is git-tracked, NOT gitignored (only submissions/tokens/ and
overrides/used/ are).
  RESOLUTION: moot given ibb-h1 is deferred entirely (see above); if/when a future arc
  builds it, this finding should be re-attached to that arc's design as an explicit
  redaction requirement.

[IMPORTANT] (feasibility-auditor + plan-skeptic, convergent) — hb-5i3 (the provider split)
was underscoped and possibly unnecessary for this arc specifically: (a) step 2's original
acceptance criteria didn't pin distinct providers per stage, so a naive re-run could
satisfy it without ever exercising the new override; (b) nightly.py's _preflight() only
validates one provider client today, so a broken PoC-authoring credential would surface
mid-run rather than failing loud upfront — real work beyond the bead's own ~30-line
estimate; (c) hb-322 already proved a simple global SECRESEARCH_LLM_PROVIDER swap stays
well within budget for a one-off supervised session — hb-5i3's real justification
(conserving the credit pool for unattended cron) isn't a concern this arc's supervised
steps actually have.
  RESOLUTION: hb-5i3 dropped from this arc entirely (design §1.4), deferred until
  unattended-cron autonomy against a real loaded target is the actual next problem.
```

## MINOR / SIGNAL

```
[MINOR] (plan-skeptic) — "local PoC-authoring proven non-viable" (hb-26v) slightly
overstates the evidence: only qwen2.5-coder-7b was actually scored (0/5); deepseek-r1-7b's
Track B was blocked by an infra crash and never completed (re-probe still open, hb-dfu).
Doesn't change any conclusion above; noted for accuracy in future framing.

[MINOR] (feasibility-auditor) — naming-collision risk between the existing
SECRESEARCH_POC_STRATEGY (templated vs. llm PoC-authoring strategy) and the now-dropped
SECRESEARCH_POC_LLM_PROVIDER — moot since the latter isn't being built in this arc, but
worth remembering if hb-5i3 is revisited later.

[SIGNAL] (feasibility-auditor) — before scoping any future ibb-h1 payload work in detail,
verify whether api.hackerone.com/v1 exposes a report-creation endpoint for researcher
accounts at all — the harder, still-unaddressed half of the original "exact
endpoint/payload deferred to plan-time" caveat.

[SIGNAL] (feasibility-auditor) — step 2's real target-vetting bar (direct, unfixed
advisory + committed lockfile) is a narrow filter requiring several rounds of trial
fetch/recon against candidates, not a single pick — reflected in design §5 (Risks) but
worth restating: budget real time for this, not zero.
```

## PRAISE (confirmed correct, kept as-is in the committed design)

```
- Excluding bugcrowd/intigriti as non-charter venues (scope-cutter): correct, they were
  never named in docs/CHARTER.md's anchor-venue list.
- Huntr's alias-to-manual-form direction itself (as opposed to building fake API
  automation huntr has no API to support) — independently confirmed correct and low-risk
  by the feasibility-auditor: submission.endpoint is a deterministic string
  (f"https://huntr.com/repos/{owner}/{pkg}"), not derived from the fragile scraped og:url
  content, so the alias doesn't inherit that fetcher's known page-drift fragility.
- The overall "validate against known ground truth before risking a live/fresh run"
  ordering shape (skeptic, feasibility-auditor) — right shape, just needed the actual
  validation mechanism replaced (see CRITICAL, revalidation step) and step 1's
  prerequisite status reconsidered (see IMPORTANT, hb-5i3) to actually deliver on that
  intent.
```

---

## Bottom line

Two of the initial draft's four steps rested on premises that don't survive contact with
the code — one architecturally (novel discovery is unreachable), one factually (the wrong
prior run, the wrong fix, the wrong root cause). A third step (Stage 7) would have
substantially widened the blast radius of a real, pre-existing, unguarded human-gate
bypass while also building real automation against two venues that turned out to be
premature on inspection. None of this was visible without reading the actual
implementation — `known_advisories` gating, `submit.py`'s status-derivation line, the
`--test-mode-confirm` flag, and `hb-7hf`'s own plan doc all had to be read directly, not
inferred from bead/retro summaries. The committed design (`2026-07-01-discovery-loop-
validation-design.md`) incorporates every resolution above; no open CRITICAL or IMPORTANT
finding remains unaddressed at the design level. Remaining work is implementation-plan
detail (§6 of the design doc), not further design revision.
