# Design: Discovery-Loop Validation & Stage 7 (huntr) Wiring

**Trace ID**: trace-20260701-001 (integration/validation epic, not a new stage)
**Status**: Planned — design approved via brainstorming + 4-agent adversarial review (see
companion `.review.md`); implementation plan written and adversarially reviewed (see
`docs/superpowers/plans/2026-07-01-discovery-loop-validation-plan.md`); not yet built.
**Charter**: `docs/CHARTER.md` (§Stages — closes the loop on the Stage 1-6 pipeline's one
real live run, and fills in the first Stage 7 submission integration)
**Predecessors**: `hb-322` (first real end-to-end run, 2026-06-30, closed — reached a
non-defensible null), `hb-be9` (verdict-trust fix, closed), `hb-26v` (Track B local-model
PoC-authoring probe, closed — established local PoC-authoring is non-viable), `hb-7hf`
(GHSA repo-asset eligibility fix, closed 2026-07-01 — **not a dependency of this work**,
see §1.1)
**Tracker**: `hb-dzz` (this workspace tracks sec-research work on the harness beads ledger,
not GitHub issues)

---

## 1. Introduction

### 1.1 Why this body of work

`hb-322` proved the pipeline runs end-to-end against real data but reached a null result
without ever exercising PoC-authoring (0 hypotheses — a genuine, correct model decision,
not a bug). The deeper question it left open — *does `claude-cli` reliably author
discriminating PoCs against a real target?* — remains untested. Separately, Stage 7
(venue-specific submission) is fully stubbed except for `manual-form` and `ghsa`, so even
a hypothetical draft finding has no path to huntr.com, the workspace's flagship anchor
venue, without falling back to the fully-manual flow.

This arc closes both gaps: validate PoC-authoring reliability cheaply and conclusively,
prove the pipeline behaves correctly against one fresh target, and wire the one Stage 7
venue integration that's actually free (huntr has no API to build against — it already
declares `manual-form` as its own real protocol).

**Correction to initial framing (2026-07-01 brainstorming):** an earlier draft of this
design assumed `hb-322` used the GHSA fetcher and that `hb-7hf` unblocked a minimatch
re-run. Both are false — `hb-322` fetched minimatch via the **huntr** fetcher, which
`hb-7hf`'s own plan doc confirms "never touches" the code path `hb-7hf` fixed. `hb-7hf` is
unrelated anchor-venue-completeness work, not a prerequisite here. See the companion
`.review.md` for the full adversarial-review disposition.

### 1.2 Purpose

Prove two things cheaply and honestly, in order:

1. **PoC-authoring reliability** — is `claude-cli` capable of authoring a discriminating
   PoC at all, independent of any live venue's current vulnerability state?
2. **Pipeline correctness on a fresh target** — does the pipeline behave correctly
   (fetch → recon → hypothesize → verify → triage) against a program it has never seen,
   reaching either a correctly-deduped known result or a defensible null?

Then wire the one Stage 7 submission path that costs near-zero new code (huntr).

### 1.3 Definition of done

- **Step 1 (PoC-authoring validation):** an `authoring_eval.py --track b` run against
  `claude-cli`, N trials (N fixed at plan time), reporting a pass rate. Any rate is a
  valid, informative result — the deliverable is the measurement, not a specific score.
- **Step 2 (fresh-target correctness proof):** a supervised `nightly.py` run against one
  never-before-loaded program reaches either **(a)** a correctly-deduped known result
  (`TRIAGE_DUPLICATE`, evidence trail intact) or **(b)** a defensible evidence-backed null.
  **Both are successes.** No submission occurs in this step.
- **Step 3 (Stage 7 huntr wiring):** `--venue huntr` dispatches through the existing
  `manual-form` handler, tagging the ledger `venue="huntr"`, with the finding's resulting
  status honestly reflecting that only the manual hand-off occurred (not a false
  `"submitted"`). Gated on the PT-2 bypass fix landing first (§3).

### 1.4 Non-goals (YAGNI)

- **Novel-vulnerability discovery.** The current pipeline is architecturally incapable of
  reaching `TRIAGE_NOVEL` for the only implemented vuln class (`dependency-cve`):
  hypothesis-gen is explicitly prompted to never invent a CVE outside the recon-fetched
  `known_advisories` list, and triage's dedup check runs against that exact same list. A
  successful verify→triage cycle can therefore only ever land on a duplicate or a null.
  Building a genuine novel-discovery pathway (an unrestricted hypothesis-gen mode plus a
  triage rule distinguishing "reachable despite a claimed fix" from a true duplicate) is a
  separate, materially larger feature — not attempted here.
- **`hb-5i3` (local-hypothesis + Claude-PoC provider split).** Neither step 1
  (`authoring_eval.py` is already provider-agnostic via the existing global
  `SECRESEARCH_LLM_PROVIDER`) nor step 2 (a supervised session, proven in-budget by
  `hb-322` with a simple global provider swap) needs per-stage routing. Its real
  justification — conserving the credit pool for *unattended* cron — isn't in scope here.
- **`ibb-h1` and `direct-maintainer` Stage 7 integrations.** Deferred: `ibb-h1`'s
  read-path payload shape is self-flagged unverified against a live account, it's unknown
  whether HackerOne's API even exposes report-creation for researcher accounts, and
  neither has a concrete finding that needs it yet. `bugcrowd`/`intigriti` are not charter
  anchor venues and stay stubbed indefinitely.
- **Multi-program fleets.** Exactly one fresh program this arc.
- **Manufacturing a finding.** No hypothesis is strained to force a non-null outcome.

---

## 2. Architecture

### 2.1 Step 1 — PoC-authoring reliability validation

Entry point: `scripts/eval/authoring_eval.py --track b`, `SECRESEARCH_LLM_PROVIDER=claude-cli`,
against the existing minimatch/CVE-2022-3517 fixture (the same fixture that already
disqualified `qwen2.5-coder-7b` at 0/5 in `hb-26v`). No live network egress beyond the
`claude-cli` calls themselves, no new PT-1 surface, bounded and predictable cost. `N` and
the pass-rate bar are implementation-plan decisions.

### 2.2 Step 2 — Fresh-target pipeline-correctness proof

Driven by `nightly.py --supervised`, reusing the existing stage functions
(`stage_recon` → `stage_hypothesize` → `stage_verify` → `stage_triage` → optionally
`stage_draft_findings`) — no new pipeline logic. Target-selection bar (real, not
cosmetic): the fetcher must succeed, recon must resolve a package-typed asset with a
**committed lockfile** (closure resolution is lockfile-gated, unchanged by `hb-7hf`), and
a known OSV/GHSA advisory must exist on a **direct** dependency edge, unfixed at the
resolved version — not transitive, which is what nulled the `hb-322` minimatch run.
Finding this candidate is real, unbudgeted vetting effort (not a single pick), addressed
at plan time. Confirm the chosen scope's `rules.ai_assistance_allowed == true` before
loading. No submission — draft (or documented null) is the terminal artifact.

### 2.3 Mandatory safety component — scope-lifecycle control

**Not present in the initial draft; added per adversarial security review.** Once step 2
loads a fresh scope, nothing today stops the pre-existing, already-registered unattended
nightly cron (`sec-research-nightly`, daily 3am, `run_unattended()`) from silently
reprocessing that scope to full draft-finding completion on every subsequent run, with no
human checkpoint — `run_unattended()` and `run_supervised()` call the identical stage
functions, and no unload/pause/TTL mechanism exists anywhere in the codebase today.
Before step 2 loads its target, this arc must add one of: (a) unload/archive the scope
once the supervised session ends, (b) a `supervised-only` flag in the scope schema that
`run_unattended()` checks and skips, or (c) a TTL/staleness gate. Mechanism choice is an
implementation-plan decision; the requirement itself is not optional — it is what makes
step 2's "no submission in this step" boundary actually real rather than merely stated.

### 2.4 Step 3 — Stage 7 huntr wiring

**Blocking prerequisite:** close the `sign_approval.py` / `sign_override.py
--test-mode-confirm` bypass first (§3). No huntr dispatch work proceeds until this lands.

Once unblocked: `--venue huntr` dispatches through the same function
`_dispatch_manual_form` already provides (opens the huntr repo page, copies the finding
body to clipboard, human pastes) — `huntr.py`'s own fetched scope already declares
`submission.protocol: "manual-form"`, so this is the technically honest integration, not a
fake API build against a venue (`api.huntr.com`) that doesn't resolve. The one required
code fix: `submit.py`'s status derivation
(`new_status = "submitted-manual" if args.venue == "manual-form" else "submitted"`, line
344) is keyed on the venue string, not on which dispatch function ran — under the current
code, aliasing huntr this way would fall to the `else` branch and record a false, fully-
confirmed `"submitted"` status. Fix: derive `new_status`/`outcome` from which dispatch
function actually executed (or an explicit confirmed-by-human bit), not from
`args.venue == "manual-form"`.

---

## 3. Prerequisite fix — PT-2 bypass (blocks step 3 only)

`scripts/sign_approval.py` and `scripts/sign_override.py` both define a
`--test-mode-confirm` flag that unconditionally sets `confirmed = True`, skipping the
interactive human-typed trace-id confirmation entirely — the single point of human control
in the whole submission pipeline. No hook in `hooks/{pretooluse,posttooluse,stop,
userpromptsubmit}.py` matches on invocations of either script (`grep` across all four
files confirms zero enforcement references — only suggested-command strings in
`override_path=` messages). `sign_token()` signs the same payload shape regardless of how
`confirmed` became `True`, so a token minted via `--test-mode-confirm` is bit-for-bit
indistinguishable from a genuine human-approved one; `submit.py`'s token validation checks
signature/expiry/trace/venue match only, never provenance.

This is pre-existing and not introduced by this design, but step 3 changes its blast
radius from low (today it can at most reach `manual-form`, where a human must still
physically paste, or `gh api`, a reviewable/revocable draft) to unbounded once any live
venue API integration exists. **Fix required before step 3 proceeds**: gate
`--test-mode-confirm` behind an environment marker provably absent outside a trusted
test-runner context, and/or add hook coverage that blocks any invocation of
`sign_approval.py`/`sign_override.py` carrying that flag without that marker. Exact
mechanism is an implementation-plan decision.

---

## 4. Guardrails (unchanged invariants, restated for this arc)

- **Scope-bounded (PT-1):** step 2's target selection loads via `fetch_program.py` before
  any recon; additionally filtered to `ai_assistance_allowed == true`.
- **Human-gated submission (PT-2):** untouched by any dispatch-handler change in step 3 —
  §3's fix closes an existing gap, it does not add a new gate. No override path is added
  or relaxed.
- **Fail-closed sandbox:** `SandboxError` (not a silently mis-scored verdict) if
  Docker-in-WSL2 is unreachable during step 2 — unchanged from the `hb-be9` fix.
- **No fabrication:** step 2's hypotheses are reported as generated; no hypothesis is
  strained to avoid a null outcome.
- **Ledger completeness:** step 3's huntr dispatch still appends to
  `submissions/ledger.jsonl` per the existing schema, unchanged event-type enum.

---

## 5. Risks

- **Step 2's target-vetting bar is a real, unbudgeted research task**, not a single pick —
  finding a program with a direct (not transitive), currently-unfixed advisory and a
  committed lockfile may take several rounds of trial `fetch_program.py`/`recon_program.py`
  runs against candidates.
- **Step 2 may still land on a null** even against a well-vetted target — this remains an
  acceptable, first-class outcome per §1.3, not a failure of the arc.
- **The scope-lifecycle mechanism (§2.3) has no existing precedent in this codebase** — it
  is new design surface, not a small addition; underestimating it repeats the pattern that
  made the original `hb-5i3` estimate (~30 lines) unreliable.

---

## 6. Open implementation-plan questions (deferred to writing-plans)

- Step 1: exact trial count `N` and what (if any) pass-rate bar constitutes "reliable
  enough" to proceed to step 2.
- Step 2: target-selection process — operator-picked candidate list vs. an automated
  scan; exact lockfile/direct-dependency vetting script, if one is worth building versus
  vetting by hand for a single target.
- §2.3: which of the three scope-lifecycle mechanisms (unload / supervised-only flag /
  TTL) to build, and its interaction with the existing scope schema.
- §3: exact `--test-mode-confirm` gating mechanism (env-marker check inside the scripts,
  new hook rule, or both).
- §3: exact status/outcome field derivation fix in `submit.py` (dispatch-function-keyed
  vs. an explicit confirmed-by-human bit threaded from the dispatcher). Resolved at plan
  time: dispatch-function-keyed, via two small pure helper functions (see the plan).
- Tracker: filed as `hb-dzz` (one umbrella epic for the arc).
