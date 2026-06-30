# hb-40u — Differential PoC version-sniffing: documented trust assumption + deferred minors

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the hb-40u R1 soundness concern (an LLM-authored trigger can discriminate by *reading the installed package version/metadata* instead of exercising the vuln → a meaningless differential → false `verified`) the way the bead's second sanctioned option prescribes — **document the residual trust assumption** — after adversarial review rejected a static detector as net-negative; then clear the genuinely-cheap deferred minors.

**Why doc-only, not a detector (the load-bearing decision):** a 3-agent adversarial plan review killed an earlier draft that shipped a regex version-sniffing detector. The detector was net-negative:

1. **Fails open on trigger naming.** It can only scan the file named in `trigger_cmd`; a trigger named `./trigger.js`, `poc.js`, or run via `node -e <inline>` is never scanned — so it misses sniffing without any adversarial effort.
2. **False-positives on a legitimate target sub-class.** Failing closed on `.version` / `package.json` makes the entire **version-parsing / semver vulnerability class** (squarely in this workspace's OSS-supply-chain target set, e.g. `node-semver`-style CVEs) permanently unverifiable, since such a vuln's *real* trigger legitimately references those tokens.
3. **No live consumer.** Novel auto-discovery is not demonstrated (`CLAUDE.md`); the only live target (minimatch) is a known CVE triage dedups to true-negative; and the **human submission gate (invariant 3, no override)** already blocks any false `verified` from being submitted — a reviewer sees a trigger that reads `package.json` trivially.

A differential oracle fundamentally cannot distinguish "discriminated via the vuln" from "via any version-correlated signal" without semantic vuln understanding. The honest resolution is to **state that assumption in the code** and lean on the existing controls (soft prompt-forbid + human gate), not to ship a bypassable guard with a real coverage cost. This is exactly the bead's sanctioned doc-only option.

**Architecture:** No new runtime logic, no new dependency. Document the trust assumption at the oracle (harness module docstring); add a one-line reinforcement of the existing no-sniff rule to the repair-feedback prompt (whose "fire ONLY on the affected version" phrasing otherwise risks nudging the model toward a version check); and clear four cheap minors (a coverage-gap test, a happy-path assertion, two clarifying comments). Cut from the prior draft after review: the static detector, the `build_plan` ecosystem re-assert (guards an unreachable state — `supports()` already gates it), and a redundant terminal ledger event (the outcome is already non-silent).

**Tech Stack:** Python 3.14, pytest. No new dependencies, no new modules.

## Global Constraints

- **No theater:** do not ship a guard that reads as "closing" the hole when it cannot. The code change is *documentation of a known residual assumption* + existing controls. The human gate (invariant 3) is and remains the load-bearing soundness invariant.
- **No validating impossible states (standing workspace rule):** do not add guards for code paths the production flow cannot reach (this is why the ecosystem re-assert was cut).
- **Fail closed elsewhere unchanged:** the oracle's existing hb-be9 "don't launder — untrusted is ERROR not REFUTED" behavior is untouched.
- **Surgical edits:** all touched files are small; edit in place.

## File Structure

- `scripts/verify/harness.py` — MODIFY: (1) add a concise "Trust assumptions (hb-40u R1)" note to the module docstring recording the residual version-sniffing assumption and *why a detector was rejected*; (2) trim the legacy single-run path comment to one factual line. [Task 1 + 2-item4]
- `scripts/verify/poc_prompt.py` — MODIFY: one-line reinforcement of the existing no-version-sniff rule in `build_poc_prompt`'s repair addendum. [Task 1]
- `scripts/verify/strategy.py` — MODIFY: one-sentence comment on `is_differential` (a degenerate identical-signature plan is still "differential"; rejected downstream by the oracle guard). [Task 2d]
- `tests/scripts/test_verify_model.py` — MODIFY: symmetric `fixed.timed_out` timeout test. [Task 2a]
- `tests/scripts/test_verify_harness_orchestrator.py` — MODIFY: assert `build_calls == 1` on the verified happy path (no spurious repair). [Task 2b]

**Explicitly cut from the prior draft (with cause):** the `detect_version_sniffing` detector (fails open + coverage cost + no consumer, above); `model.py` changes; the `build_plan` ecosystem re-assert (`supports()` already gates `==npm`; `verify_hypotheses` always calls `supports()` before `build_plan` — guarding it validates an unreachable state); the terminal `verify-no-discrimination` ledger event (the path already emits `verify-verdict` with reason `differential: no-discrimination` — not silent).

---

## Task 1: Document the R1 residual trust assumption

**Files:**
- Modify: `scripts/verify/harness.py`, `scripts/verify/poc_prompt.py`

- [x] **Step 1: Add the trust-assumptions note to the harness module docstring**

In `scripts/verify/harness.py`, append to the module docstring (top of file):

```
Trust assumptions (hb-40u R1): the differential oracle proves a trigger discriminates
the AFFECTED from the FIXED version — NOT that it did so by exercising the
vulnerability. A trigger that reads the installed version/metadata (e.g.
require('pkg/package.json').version) would discriminate without proving anything,
yielding a false 'verified'. This residual assumption is accepted, not enforced in
code: a static detector was evaluated (hb-40u) and rejected — it fails open on trigger
naming and would false-positive on the legitimate version-parsing vulnerability class.
The controls are the soft prompt-forbid (poc_prompt.SYSTEM) and the load-bearing human
submission gate (invariant 3): no finding is submitted on an oracle verdict alone.
```

- [x] **Step 2: Reinforce the no-sniff rule in the repair-feedback prompt**

In `scripts/verify/poc_prompt.py`, in `build_poc_prompt`'s `if repair_context:` block, the addendum currently ends with `"...fires ONLY on the affected version."`. Append (the "fire ONLY on affected" nudge otherwise invites a version check):

```python
            " Discriminate by exercising the vulnerable behaviour, never by reading the "
            "installed version or package.json — a version check is not a proof."
```

- [x] **Step 3: Verify nothing regressed**

Run: `cd C:/Users/Garre/Workspace/sec-research && python -m pytest tests/scripts/test_verify_poc_prompt.py tests/scripts/test_verify_harness_orchestrator.py -q`
Expected: PASS (docstring + prompt-text changes touch no asserted behavior; if `test_verify_poc_prompt.py` does not exist, run the full suite in Task 2 Step 4 instead).

- [x] **Step 4: Commit**

```bash
git add scripts/verify/harness.py scripts/verify/poc_prompt.py
git commit -m "docs(sec-research): hb-40u document differential-oracle version-sniffing trust assumption"
```
(Commit only on explicit authorization — deliver landing gate.)

---

## Task 2: Cheap deferred minors (coverage + clarifying comments)

**Files:**
- Modify: `scripts/verify/strategy.py`, `tests/scripts/test_verify_model.py`, `tests/scripts/test_verify_harness_orchestrator.py`

- [x] **Step 1: (2a) Symmetric `fixed.timed_out` timeout test**

In `tests/scripts/test_verify_model.py`, after `test_differential_timeout_is_error`, add:

```python
def test_differential_fixed_side_timeout_is_error():
    from verify.model import derive_differential_verdict, VERDICT_ERROR
    plan = _diff_plan()
    affected = _trigger(exit_code=0, sha="confirmed")
    fixed = _trigger(timed_out=True)
    assert derive_differential_verdict(affected, fixed, plan) == (VERDICT_ERROR, "timeout")
```

Run: `python -m pytest tests/scripts/test_verify_model.py -q -k fixed_side_timeout` → PASS (the oracle already checks `affected.timed_out or fixed.timed_out`; this closes the asymmetric-coverage gap).

- [x] **Step 2: (2b) Assert `build_calls == 1` on the verified happy path**

In `tests/scripts/test_verify_harness_orchestrator.py`, modify `test_differential_verified` to prove a verified-on-first-try plan triggers exactly one `build_plan` call (no spurious repair). Replace its `strategy = _FakeStrategy(supports=True, plan=_make_diff_plan())` with:

```python
    strategy = _RepairStrategy(first=_make_diff_plan(), second=_make_diff_plan())
```

and add after the existing verdict assertions:

```python
    assert strategy.build_calls == 1  # verified on first try -> no repair re-author
```

(`_RepairStrategy` counts `build_calls`; the faked `_drive_differential` returns the verified/patched pair, so no repair occurs.)

Run: `python -m pytest tests/scripts/test_verify_harness_orchestrator.py -q -k differential_verified` → PASS.

- [x] **Step 3: (2d + item4) Clarifying comments**

In `scripts/verify/strategy.py`, append to the `is_differential` docstring:

```
Note: a True result does NOT require the refuted signature to differ from the verified
one — a degenerate (identical-signature) plan is still 'differential' here and is
rejected downstream by the oracle's degenerate-signature guard.
```

In `scripts/verify/harness.py`, on the legacy single-run path (the `# ---- legacy single-run path ...` comment block), append one factual line:

```
# NOTE: uses the weaker single-run oracle; currently unreachable — both registered
# strategies emit differential plans (a non-differential template would re-activate it).
```

- [x] **Step 4: Run the full suite**

Run: `cd C:/Users/Garre/Workspace/sec-research && python -m pytest -q`
Expected: PASS (prior green + the two new/changed tests; no failures).

- [x] **Step 5: Commit**

```bash
git add scripts/verify/strategy.py tests/scripts/test_verify_model.py \
        tests/scripts/test_verify_harness_orchestrator.py
git commit -m "chore(sec-research): hb-40u deferred minors — timeout-symmetry + happy-path coverage, clarifying comments"
```
(Commit only on explicit authorization.)

---

## Verification

- `python -m pytest -q` — full offline suite green, including the two added/changed tests.
- The harness module docstring records the R1 residual trust assumption and the detector-rejection rationale; the repair prompt reinforces the no-sniff rule.
- No new runtime logic, no new module, no guard on an unreachable path — the change is documentation + the existing controls + cheap coverage.

## Out of scope / follow-ups

- **Static version-sniffing detector** — evaluated and rejected (fails open on trigger naming; false-positives on the version-parsing vuln class; no live consumer). Recorded in the harness docstring, not shipped.
- **Version-string normalization across both containers** — would defeat the most common naive sniff without the detector's coverage cost, but is a complex install-rewrite step that is still incomplete (misses `npm ls` / hardcoded VERSION constants). Out of scope for a P3 with no live consumer; revisit only if/when novel auto-discovery makes a false `verified` reachable past the human gate.
- **Sandbox `--read-only` trigger hardening** — tracked separately (hb-nxz).
- **`build_plan` ecosystem re-assert** — cut: `supports()` already gates `==npm` and is always called first; guarding it validates an unreachable state.
- **Legacy single-run `derive_verdict` removal** — documented inline, not removed (a future non-differential template could legitimately need it).

## Retrospective

_(to be completed post-execution via `/plan-retrospective`)_
