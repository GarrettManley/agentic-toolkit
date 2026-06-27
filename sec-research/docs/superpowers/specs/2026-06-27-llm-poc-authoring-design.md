# Design: LLM PoC Authoring with a Differential Trust Oracle

**Trace ID**: trace-20260627-002 (Stage 4 — discovery-capability build)
**Status**: Draft
**Charter**: `docs/CHARTER.md` (§Stages 4 — closes the "wired pipeline → discovery engine" gap; §Invariant 2 evidence-grounded)
**Predecessors**: Stage 4a sandbox (hb-wy4), 4b hypothesis-gen (hb-oec), 4c verify harness (hb-s2c) — all shipped and live-proven on the minimatch fixture (2026-06-26)
**Tracker**: hb-ane (depends on hb-be9; unblocks hb-322 first-real-run)
**Supersedes (as prerequisite)**: `2026-06-27-first-real-run-huntr-design.md` — the adversarial review of that spec found the real run cannot produce a genuine outcome until this capability exists.

---

## 1. Introduction

### 1.1 Why this is the highest-value work

The pipeline is wired end-to-end, but it can only author a PoC for **one hand-written
template** (`npm/minimatch/CVE-2022-3517`). `verify/llm_strategy.py` is a deliberate
`NotImplementedError` seam. So for any other program, every hypothesis falls through to
`VERDICT_SKIPPED` — no verification, no draft. **The gap between "wired pipeline" and
"discovery engine" is exactly this: PoC authoring for hypotheses we did not pre-template.**
An adversarial review of the proposed first-real-run (hb-322) surfaced this as the
premise-breaker; this spec is the prerequisite that makes that run meaningful.

### 1.2 The hard problem: trust, not LLM plumbing

Calling an LLM to emit a PoC is easy. The danger is the project's core failure mode: an LLM
can trivially write a trigger that prints the success sentinel **unconditionally**,
manufacturing a false-positive "verified" finding — AI-slop at the strategy layer, the exact
thing this workspace exists to prevent.

The existing verdict model is deterministic (a constant-sentinel string + fixed exit code →
`expected_trigger_sha256`). The minimatch template is already a *differential* probe
(`VULN_CONFIRMED` on 3.0.4, `PATCHED` on 3.0.5) — but the guarantee that it actually
**discriminates** patched from vulnerable lives in the human author's verification against
the source diff. **An LLM author gets no such trust. The harness must prove discrimination
by execution.**

### 1.3 The solution: a differential trust oracle

Run the *same* authored PoC against **two** installs of the package:

| Install | Required signal | Meaning |
|---------|-----------------|---------|
| **affected** version | emits `VULN_CONFIRMED` (verified signature) | the exploit fires on the vulnerable code |
| **fixed** version | does **not** emit it (refuted signature) | the exploit is silenced by the fix |

`verified` is granted **only if both hold**. A PoC that confirms on the fixed version too is
not testing the vulnerability — it is rejected as `VERDICT_ERROR`, never laundered into a
verdict. **Trust comes from the differential execution, not from trusting the LLM's claim or
the advisory text.** This is the non-negotiable anti-slop spine of the design.

This also resolves **hb-be9**: the `expected_refuted` signature it calls for *is* the
fixed-version oracle. hb-be9 is not a separate fix — it is folded in here as the second half
of the differential.

### 1.4 Definition of done

- `LLMPocStrategy.supports()` returns `True` for npm `dependency-cve` hypotheses carrying an
  affected + fixed version; `build_plan()` authors a `PocPlan` via the LLM.
- The harness drives the plan **differentially** (affected + fixed) and grants `verified`
  only on a clean discriminating result; non-discrimination and infra failures → `error`
  (with one bounded LLM repair retry on non-discrimination).
- Re-running the existing minimatch path under the new differential drive still yields
  `verified` for 3.0.4 / `refuted` for 3.0.5 (no regression).
- All existing Stage-4c tests pass (with documented updates where the verdict contract
  changed); new tests cover authoring, the differential oracle, the repair retry, and the
  slop-rejection path.

### 1.5 Non-goals (YAGNI)

- **Ecosystems beyond npm** (PyPI/cargo/rubygems) — each needs its own sandbox install/trigger
  runtime; deferred (overlaps hb-nxz hardening).
- **Novel vuln classes with no CVE/fixed-version** — the differential oracle needs a fixed
  version; no-fix-diff novel discovery is a later, separately-justified step.
- **Fix-diff extraction during recon** — the diff is an optional authoring aid, not a trust
  dependency (§3.4); deferred.
- **The first-real-run epic (hb-322)** itself — this spec unblocks it; running it is the next
  body of work.
- **Submission (Stage 7)** — untouched.

---

## 2. Architecture

### 2.1 Component map (new vs. reused)

```
                 hypothesis (npm dependency-cve, affected+fixed versions)
                          │
                          ▼
   NEW  ┌─────────────────────────────────┐
        │ LLMPocStrategy.build_plan        │  prompt + grammar-constrained JSON
        │  (verify/llm_strategy.py)        │  (mirrors llm/generate.py pattern)
        └─────────────────────────────────┘
                          │ PocPlan (+ expected_refuted signature)
                          ▼
   NEW  ┌─────────────────────────────────┐   reuse  ┌──────────────────────┐
        │ differential drive in harness.py │ ───────► │ scripts/sandbox/     │
        │  run plan @affected AND @fixed   │          │ (unchanged)          │
        └─────────────────────────────────┘          └──────────────────────┘
                          │ (affected_ev, fixed_ev)
                          ▼
   NEW  ┌─────────────────────────────────┐
        │ derive_verdict (model.py)        │  verified iff affected=confirmed
        │  + expected_refuted (hb-be9)     │  AND fixed=refuted; else error
        └─────────────────────────────────┘
                          │ Verdict → reuse: ledger, _persist, Stage 5/6
```

**Reused unchanged:** the Stage-4a sandbox; the `PocStrategy` Protocol + `select_strategy("llm")`
dispatch; the deterministic sentinel verdict core; ledger / `_persist`; the LLM client
(`llm/client.py`, `complete_json`).

### 2.2 `LLMPocStrategy`

- `supports(hypothesis)` → `True` iff `vuln_class == "dependency-cve"`, `evidence_seed`
  ecosystem is `npm`, and an **affected and a fixed version** are resolvable (the fixed
  version comes from the recon advisory; see §3.3).
- `build_plan(hypothesis)` → builds a PoC-authoring prompt (advisory facts, package,
  affected+fixed versions, attack-vector hypothesis), calls `client.complete_json` with a
  **grammar-constrained JSON schema** for the PoC, and materializes the response into a
  `PocPlan`. Raises `SeedIncomplete` if the seed lacks required fields (same contract as the
  templated strategy, so `verify_hypotheses` handles it identically).

### 2.3 Authored-PoC JSON contract (LLM output schema)

The LLM returns exactly: `files` (map of filename→content: the trigger script + manifest),
`install_target` (package name; versions are injected by the harness, not the LLM — see
§3.1), `trigger_cmd`, `sentinel_confirmed` (constant string), `expected_exit`, and a short
`reasoning` field for the journal/evidence. `build_plan` computes `expected_trigger_sha256 =
sha256(sentinel_confirmed + "\n")` offline (exactly as the template does) — the LLM never
supplies a hash.

### 2.4 Differential drive + verdict

`harness.py` gains a differential path: materialize the plan once, run the install→trigger
phases against the **affected** version, then against the **fixed** version (the only change
between runs is the `install_cmd` version pin). `derive_verdict` is extended with the
`expected_refuted` signature:

- affected run matches **verified** signature **AND** fixed run matches **refuted**
  signature → `VERDICT_VERIFIED`.
- affected matches refuted (exploit didn't fire on vulnerable code) → `VERDICT_REFUTED`.
- affected confirms **AND** fixed also confirms (no discrimination) → `VERDICT_ERROR`
  ("poc-does-not-discriminate") → triggers the repair retry (§2.5).
- trigger output matching **neither** signature, timeout, or `SandboxError` → `VERDICT_ERROR`
  (infra / indeterminate) — **never** silently `refuted` (this is the hb-be9 correctness fix).

### 2.5 Bounded repair retry

On a `poc-does-not-discriminate` error, feed the failure (both runs' outputs) back to the LLM
for **exactly one** re-author attempt. If the re-authored PoC still fails to discriminate →
final `VERDICT_ERROR`. Retry count is a named constant; the retry is logged to the ledger.
No unbounded loops.

---

## 3. Data dependencies & threading

### 3.1 Versions are harness-controlled, not LLM-controlled

The affected and fixed version strings are injected by `build_plan` into the two
`install_cmd`s; the LLM authors a version-agnostic trigger. This keeps the LLM unable to
"cheat" the version boundary and keeps installs deterministic.

### 3.2 Required `evidence_seed` fields

`package_ecosystem`, `package_name`, `affected_versions_range`, `candidate_cve_id` (already
the templated contract) **plus** a resolvable **fixed version** (§3.3).

### 3.3 Fixed version source (verified available)

Recon already extracts the fixed version into `known_advisories[].fixed` (from OSV
`ranges[].events[].fixed`; see `scripts/recon/advisories.py`). It is **not** currently a
named `evidence_seed` field. This spec threads it through: either Stage-4b carries
`fixed_version` into the seed, or `build_plan` reads it from the hypothesis's `recon_ref`
back to the recon item. (Which of the two is an implementation-plan decision; both are small
and the data exists.)

### 3.4 Fix-diff is an optional authoring aid, not a trust dependency

A richer prompt could include the actual fix diff (derivable locally from the
already-cloned repo between the affected and fixed tags — `recon_item.repo.clone_path` +
`commit_sha`). It improves authoring quality but is **not** required: the differential
oracle's trust rests entirely on the two version executions. Deferred to a follow-up.

---

## 4. Safety & guardrails (reuse + restate)

- **Sandbox unchanged & fail-closed.** Trigger runs `--network none`; install is gated by
  `check_http(network_allow=install_hosts)`. docker-unreachable → `SandboxError` → `error`,
  never host-run.
- **LLM authors data, not host actions.** The PoC files only ever execute *inside* the
  sandbox. `build_plan` does no host execution.
- **`install_hosts`** for npm is the registry only (`registry.npmjs.org`), set by the
  harness, not the LLM.
- **Determinism.** Constant sentinel + offline-computed hash; LLM never supplies the hash or
  the version pins.
- **Bounded LLM use.** One authoring call + at most one repair call per hypothesis.

---

## 5. Testing

- **Offline (default):** inject a fake `LLMClient` returning a canned PoC JSON and a fake
  `runner` returning canned sandbox results; assert authoring, the differential verdict
  matrix (verified / refuted / non-discriminate→error / infra→error), and the repair retry
  (one canned failure then a canned success).
- **Existing minimatch regression:** the differential drive must still yield verified@3.0.4 /
  refuted@3.0.5; update the existing `derive_verdict` refuted-vs-error tests to the new
  contract and document each change.
- **Live (gated, `VERIFY_LIVE=1` / `LLM_LIVE=1`):** author + differentially verify one real
  npm dependency-CVE with a known fixed version, end to end, against real Docker.

---

## 6. Risks

- **LLM cannot author a discriminating PoC for many real CVEs.** Likely true for a fraction
  of the class; the oracle correctly rejects those as `error` rather than guessing — that is
  the design working, not failing. The *rate* of authorable CVEs is the key empirical unknown
  and is itself valuable signal.
- **Existing-test churn.** Changing the verdict contract (refuted-vs-error, differential)
  touches Stage-4c tests; enumerated and updated, not silently broken.
- **PocPlan schema change.** Adding `expected_refuted` fields to a frozen dataclass must use
  optional-with-default to avoid breaking every constructor site at once (implementation-plan
  detail; flagged by the adversarial review).

---

## 7. Open implementation-plan questions (deferred to writing-plans)

- Fixed-version threading: Stage-4b seed field vs. `build_plan` reading `recon_ref`.
- `expected_refuted` representation on `PocPlan` (separate exit+sha fields vs. a nested
  signature object) and the optional-default migration for the frozen dataclass.
- PoC-authoring prompt + JSON-grammar schema location (under `verify/` vs. reuse `llm/`).
- Exact phrasing of the slop-rejection ledger events and journal capture.
