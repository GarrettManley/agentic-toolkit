# Design: First Real End-to-End Run (sec-research × huntr.com)

**Trace ID**: trace-20260627-001 (integration/validation epic, not a new stage)
**Status**: DEFERRED — blocked on a prerequisite. Adversarial review (`*.review.md`) found the run cannot produce a genuine outcome until LLM PoC authoring exists; that prerequisite is now `2026-06-27-llm-poc-authoring-design.md` (tracker hb-ane). Revisit this spec (and re-review it against the findings file) once hb-ane lands.
**Status (original)**: Draft
**Charter**: `docs/CHARTER.md` (§Stages — exercises the full Stage 1–6 pipeline against real data for the first time)
**Predecessors**: Stages 1–6 wired and live-proven on the minimatch known-CVE fixture (Stage 4 Docker activation 2026-06-26, trackers hb-ctr + hb-s2c)
**Tracker**: hb-322 (depends on / blocked by hb-be9)

---

## 1. Introduction

### 1.1 Why this body of work

The pipeline is wired end-to-end — intake (Stage 2) → recon (Stage 3) → hypothesis +
sandboxed verify (Stage 4) → triage/dedup (Stage 5) → draft (Stage 6) — and has been
proven *mechanically* live: the 2026-06-26 Docker activation ran the sandbox/verify
harness against the **minimatch CVE-2022-3517 fixture** (348 pass / 1 skip). But that is
a *known* CVE: triage dedups it by design, so it produces no draft. The machine has never
touched a real loaded bounty program.

This epic is the moment-of-truth integration: drive the whole pipeline against **one real
huntr.com program** and find out whether it produces a trustworthy, non-slop outcome
against data nobody fixtured in advance. Everything before this was building the machine;
this is the first time we run it for real.

### 1.2 Purpose

Prove the **pipeline against real data**, not luck. Whether a novel vulnerability exists
in any given program is non-deterministic — so the deliverable is defined around what we
control: a fully-instrumented, observable run with a **trustworthy verdict either way**.

### 1.3 Definition of done

A supervised end-to-end run against one real huntr.com program that yields a **trustworthy
outcome**:

- **(a)** a draft-quality finding — PoC at `findings/<trace>/poc/reproduce.sh`, captured
  execution evidence, and a Tier-1 `Citation:` — **or**
- **(b)** a defensible, evidence-backed **null result**: "nothing confirmed; here is the
  full audit trail of every hypothesis generated and why each was refuted, deduped, or
  flagged inconclusive."

**Both are successes.** The thing proven is that the pipeline behaves correctly and
honestly on real input. A clean null result is a *first-class win*, not a failure.

### 1.4 Non-goals (YAGNI)

- **Stage 7** (submission maturation, self-improvement) — out of scope. Even a confirmed
  draft stops at draft; the human-signed approval gate is never touched.
- **Multi-program fleets** — exactly one program this run.
- **Nightly-cron handoff** — that is the *reward* after this proves out, a follow-up, not
  part of this work.
- **Full sandbox hardening (hb-nxz)** — only the slice hb-be9 requires.
- **Manufacturing a finding** — we will never fabricate or strain a hypothesis to force a
  non-null outcome. That is the exact anti-AI-slop failure this workspace exists to prevent.

---

## 2. Architecture: the run as six gated checkpoints

The run is the existing pipeline driven **supervised, stage-by-stage**. Each stage runs,
then **halts for inspection** before the next is invoked. At each checkpoint, real data
either flows through cleanly or exposes a fixture-vs-reality gap, which we reconcile in
place before continuing. (The live-reconcile gaps hb-dzu / hb-bpd are *expected* to surface
here — surfacing and closing them is part of the work.)

| # | Stage | Entry point | Real-data risk to watch | Checkpoint artifact |
|---|-------|-------------|-------------------------|---------------------|
| 1 | **Intake** | `scripts/fetch_program.py` (huntr) | `__NEXT_DATA__` response-shape drift (hb-dzu); invalid scope must route to `scope.draft.yaml`, never live | a **live** `scope.yaml` for one real program |
| 2 | **Recon** | `scripts/recon_program.py` | registry-metadata + lockfile + clone caps (2000 deps / 500MB); OSV batch response shape (hb-bpd) | schema-valid recon item(s) in `runtime/recon/<slug>/` |
| 3 | **Hypothesis** | `scripts/llm/` (generate) | LLM emits *testable, scope-bounded* PoC plans — not slop; each plan declares verified **and** refuted signatures (see §3) | `runtime/hypotheses/<slug>/hypotheses.json` |
| 4 | **Verify** | `scripts/sandbox/` + `scripts/verify/harness.py` | infra-failure laundering (**hb-be9**); fail-closed sandbox; uid-1000 execute hardening | per-hypothesis verdict + sandbox evidence |
| 5 | **Triage** | `scripts/triage/` (dedup) | dedup vs NVD/GHSA/OSV/program `disclosed/` on *real* CVE identifiers | dedup decision + rationale per candidate |
| 6 | **Draft** | `scripts/draft/` (drafter) | fires only on **novel + confirmed**; otherwise documents the null | finding draft **or** documented null result |

### 2.1 Driver

The supervised driver is a thin orchestration over the existing stage functions
(`nightly.py` already composes `stage_recon` etc.). This epic does **not** rewrite the
pipeline — it invokes each stage with an inspection halt between them, capturing each
checkpoint's outcome to the run journal (§4). Whether the driver is a new
`--supervised`/`--until <stage>` flag on the existing entry points or a small dedicated
run script is an implementation-plan decision; either way it reuses the existing stage
code, adds no new pipeline logic, and writes nothing the nightly path doesn't already write
(plus the journal).

---

## 3. hb-be9 verdict-trust fix (Stage-4 prerequisite, rides along)

A **null result** (done-criterion *b*) is only defensible if `refuted` genuinely means
"not vulnerable" rather than "the container OOM'd / hit a uid-1000 permission denial /
couldn't import a module." Today `derive_verdict` (`scripts/verify/model.py`) maps **any**
non-`(exit0 + VULN_CONFIRMED-hash)` trigger result to `VERDICT_REFUTED`, and `trigger.js`'s
catch is correspondingly too broad. That silently launders infra failures into false
negatives — the precise failure this workspace exists to prevent.

This is the **only new build** in the epic; everything else exercises existing code. Minimal
scope:

- **PoC plan / strategy schema** gains an **`expected_refuted` signature**
  (`expected_refuted_exit` + `sha256`) alongside the existing verified signature, so a
  template declares what *both* a confirmed and a genuinely-patched run look like.
- **`derive_verdict`** returns **`VERDICT_ERROR`** when trigger output matches *neither* the
  verified nor the refuted signature (instead of defaulting to `REFUTED`).
- **`harness._drive_phased`** adds a **trigger-phase infra guard** mirroring the existing
  install-phase `SandboxError` path.
- **`trigger.js`** catch narrowed to only the length-guard error it legitimately handles;
  any other throw becomes `ERROR`, not `PATCHED`.
- **Tests** for each signature path (verified / refuted / error) and **all exploit
  templates** updated to declare both signatures.

The minimatch live path is empirically immune (3.0.4 verified *through* the uid-1000
trigger in the 348-pass run), so this fix is additive, not a regression repair — but it is
load-bearing for trusting any `refuted` verdict a real run produces.

---

## 4. Observability & evidence

Every stage already appends to the **hash-chained ledger** and writes under `runtime/` and
`findings/<trace>/`. This epic adds **one run journal** — a single document capturing, in
order:

- the program chosen and why (in-scope, real, tractable);
- each checkpoint's outcome (pass / gap-found-and-fixed);
- every live-reconcile gap hit and the exact reconcile applied;
- the final verdict for every hypothesis with its evidence trail;
- the overall outcome: draft path or documented null.

**This journal is the proof artifact** regardless of draft-vs-null. It is what makes a null
result defensible and a draft result auditable. It lives alongside the run under
`runtime/` (exact path an implementation-plan detail).

---

## 5. Guardrails (unchanged invariants, restated for a live run)

- **Scope:** all network egress stays gated through `policy.check_http`; in-scope hosts
  only. Real egress this run = huntr metadata fetch, registry installs, `git clone` — all
  already on the gated path.
- **No submission.** Stage 7 is out of scope; the draft is the terminal artifact; the
  human-signed approval token is never generated or used.
- **Fail-closed sandbox.** docker-unreachable → `SandboxError`, never a host-run of the
  untrusted PoC.
- **No fabrication.** Hypotheses that don't verify are reported as such; we do not strain
  to produce a non-null outcome.

---

## 6. Risks

- **Intake / recon break on real response shapes** — *expected*; that is why the run is
  supervised. Fixes are small, localized reconciles (hb-dzu / hb-bpd), captured in the
  journal.
- **LLM hypothesis quality is the real unknown** — whether Stage 3/4b generates *testable*
  plans or slop against a real package is the open question. Either answer is valuable
  intelligence about the pipeline and gets recorded honestly.
- **Real run finds nothing confirmable** — this is an acceptable, expected, first-class
  outcome (done-criterion *b*), not a failure of the epic.

---

## 7. Open implementation-plan questions (deferred to writing-plans)

- Supervised driver shape: flag on existing entry points vs. dedicated run script.
- Run-journal exact location and format.
- Program-selection mechanism: pipeline-chosen from huntr listing vs. operator-picked
  in-scope program for this first run.
- Ordering of the hb-be9 fix relative to first invocation (recommended: land hb-be9 +
  tests *before* Stage-4 checkpoint of the real run, so the first real verdict is already
  trustworthy).
