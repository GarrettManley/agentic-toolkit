# hb-0vq Seed-Field Alignment Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make local-model `dependency-cve` authoring score seed-complete by aligning the
authoring/scoring path with what models emit — one shared, recon-aware normalization used by
**both** `generate_hypotheses` (production) and `score_track_a` (eval), so the eval stays an
honest proxy for production, and so package identity + install version are recon ground truth
(not model-authored).

**Architecture:** The 2026-06-30 verdict proved offline (0/6 → 6/6) that local models author
*correct* hypotheses but fail `seed_complete` on three gaps: missing `target.version_or_revision`,
`cve_id` key drift, and ecosystem/name in `target` not `evidence_seed`. This fix adds
`_normalize_authored(h, item)` in `llm/generate.py`, wires it into both paths, and adds one
alias. **Trust-hardening (from plan review):** `package_ecosystem`/`package_name` and
`target.version_or_revision` are **recon ground truth — overwritten/dropped, never trusted from
the model** — because `seed["package_name"]` feeds `npm install` (`llm_strategy.py:91`) and
`is_in_scope` gates on `target.identifier`, not the seed, so a model-supplied package name would
otherwise bypass scope. `candidate_cve_id` stays model-authored (it is the hypothesis's claim;
`_resolve_fixed_version` is its implicit cross-check). All recon-stamping is scoped to
`vuln_class == "dependency-cve"`.

**Tech Stack:** Python 3.14, `pytest`, `jsonschema` (Draft 2020-12).

**Tracker:** bead `hb-0vq` (P2) — the verdict's specified next action.

## Global Constraints

- **Eval ↔ production parity is the point.** The normalization MUST be one function called by
  both `generate_hypotheses` and `score_track_a`. Do not fork the logic.
- **Trust boundary.** For `dependency-cve`: `package_ecosystem`/`package_name` ← recon `asset`
  (overwrite); `target.version_or_revision` ← recon `resolved_version` (stamp if present, **pop
  if absent**). `candidate_cve_id` stays model-authored. `fixed_version` (`_resolve_fixed_version`)
  unchanged. Non-`dependency-cve` hypotheses are left untouched by the recon stamping.
- **No prompt changes** — boundary normalization is sufficient and proven. Prompt-hardening is a
  noted follow-up.
- **Reference fixture:** `tests/fixtures/llm/recon_item_minimatch.json` (`resolved_version 3.0.4`,
  `asset.ecosystem npm`, `asset.identifier minimatch`).
- **Schema note (verified in review):** `target.version_or_revision` is a declared target
  property (`hypothesis.schema.json:20`) — stamping it is schema-valid. `rationale` has
  `minLength:40` (`:37`) — any test hypothesis must use a ≥40-char rationale or validation
  rejects it before `seed_complete` runs.

---

### Task 1: Recon-aware shared normalization, wired into production + eval (TDD)

**Files:**
- Modify: `scripts/llm/generate.py` (`_SEED_KEY_ALIASES` L50-53; add `_normalize_authored`; call site L122)
- Modify: `scripts/eval/authoring_eval.py` (import L38; `score_track_a` call L100)
- Create: `tests/scripts/test_generate.py`
- Modify: `tests/scripts/test_authoring_eval.py` (append the parity test)

**Interfaces:**
- Produces: `_normalize_authored(h: dict, item: dict) -> None` — mutates `h`: normalize seed
  aliases (backfill-only); then, **only if `h["vuln_class"] == "dependency-cve"`**, overwrite
  `evidence_seed.package_ecosystem`/`package_name` from `item["asset"]`, and set
  `h["target"]["version_or_revision"]` from `item["resolved_version"]` (pop it if absent).

- [x] **Step 1: Write failing unit tests.**

```python
# tests/scripts/test_generate.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
from llm.generate import _normalize_authored

ITEM = {"slug": "huntr-npm-minimatch",
        "asset": {"asset_type": "package", "identifier": "minimatch", "ecosystem": "npm"},
        "resolved_version": "3.0.4"}

def _h(target, seed, vuln_class="dependency-cve"):
    return {"vuln_class": vuln_class, "target": dict(target), "evidence_seed": dict(seed)}

def test_cve_id_aliases_map_to_candidate():
    for key in ("cve_id", "cve_id_proposed_or_assigned"):
        h = _h({"identifier": "minimatch"}, {key: "CVE-2022-3517"})
        _normalize_authored(h, ITEM)
        assert h["evidence_seed"]["candidate_cve_id"] == "CVE-2022-3517"

def test_recon_overwrites_package_identity():
    # model supplies WRONG ecosystem/name -> recon ground truth wins (feeds npm install + scope)
    h = _h({"identifier": "minimatch"},
           {"candidate_cve_id": "CVE-2022-3517", "package_ecosystem": "pypi", "package_name": "evil"})
    _normalize_authored(h, ITEM)
    s = h["evidence_seed"]
    assert s["package_ecosystem"] == "npm" and s["package_name"] == "minimatch"

def test_backfills_package_identity_when_seed_omits_it():
    h = _h({"identifier": "minimatch", "ecosystem": "npm"}, {"candidate_cve_id": "CVE-2022-3517"})
    _normalize_authored(h, ITEM)
    s = h["evidence_seed"]
    assert s["package_ecosystem"] == "npm" and s["package_name"] == "minimatch"

def test_stamps_target_version_from_recon():
    h = _h({"identifier": "minimatch"}, {"candidate_cve_id": "CVE-2022-3517"})
    _normalize_authored(h, ITEM)
    assert h["target"]["version_or_revision"] == "3.0.4"

def test_drops_model_version_when_recon_absent():
    h = _h({"identifier": "minimatch", "version_or_revision": "9.9.9"}, {"candidate_cve_id": "x"})
    _normalize_authored(h, {"asset": {"identifier": "minimatch", "ecosystem": "npm"}})  # no resolved_version
    assert "version_or_revision" not in h["target"]   # model-authored install target dropped

def test_preserves_model_candidate_cve_id():
    h = _h({"identifier": "minimatch"}, {"candidate_cve_id": "CVE-2022-3517"})
    _normalize_authored(h, ITEM)
    assert h["evidence_seed"]["candidate_cve_id"] == "CVE-2022-3517"

def test_non_dependency_cve_left_untouched():
    h = _h({"identifier": "x"}, {"candidate_cve_id": "y"}, vuln_class="logic-flaw")
    _normalize_authored(h, ITEM)
    assert "package_ecosystem" not in h["evidence_seed"]
    assert "version_or_revision" not in h["target"]
```

- [x] **Step 2: Run — verify fail.**

Run: `cd C:/Users/Garre/Workspace/sec-research && python -m pytest tests/scripts/test_generate.py -q`
Expected: FAIL (`ImportError: cannot import name '_normalize_authored'`).

- [x] **Step 3: Implement in `scripts/llm/generate.py`.**

Add one alias (keep existing two):
```python
_SEED_KEY_ALIASES = {
    "cve_id_proposed_or_assigned": "candidate_cve_id",
    "cve_id": "candidate_cve_id",
    "attack_vector": "attack_vector_hypothesis",
}
```
Add after `_normalize_seed_keys`:
```python
def _normalize_authored(h: dict, item: dict) -> None:
    """Align a model-authored hypothesis with the seed-completeness gate at the system
    boundary. Seed-key aliases are backfill-only. For dependency-cve, package identity and
    the install version are RECON GROUND TRUTH, not model-authored: package_ecosystem/name
    feed `npm install` and the scope check keys on target.identifier (not the seed), so a
    model-supplied package name must never ride through; the install version is dropped when
    recon cannot supply it (mirrors _resolve_fixed_version's defensive pop). candidate_cve_id
    stays model-authored — it is the hypothesis's claim, cross-checked by _resolve_fixed_version."""
    seed = h.setdefault("evidence_seed", {})
    _normalize_seed_keys(seed)
    if h.get("vuln_class") != "dependency-cve":
        return
    asset = item.get("asset", {}) or {}
    if asset.get("ecosystem"):
        seed["package_ecosystem"] = asset["ecosystem"]
    if asset.get("identifier"):
        seed["package_name"] = asset["identifier"]
    tgt = h.setdefault("target", {})
    resolved = item.get("resolved_version")
    if resolved:
        tgt["version_or_revision"] = resolved
    else:
        tgt.pop("version_or_revision", None)
```

- [x] **Step 4: Run unit tests — verify pass.**

Run: `python -m pytest tests/scripts/test_generate.py -q`
Expected: PASS (7 passed).

- [x] **Step 5: Wire into both paths.**
  - `scripts/llm/generate.py:122` — replace `_normalize_seed_keys(h.setdefault("evidence_seed", {}))`
    with `_normalize_authored(h, item)`. Leave L127-128 (`seed = ...` + `_resolve_fixed_version`) unchanged.
  - `scripts/eval/authoring_eval.py:38` — change `from llm.generate import _normalize_seed_keys`
    to `from llm.generate import _normalize_authored`.
  - `scripts/eval/authoring_eval.py` `score_track_a` (L100) — replace
    `_normalize_seed_keys(h.setdefault("evidence_seed", {}))` with `_normalize_authored(h, recon_item)`.

- [x] **Step 6: Write the eval-parity test** (append to `tests/scripts/test_authoring_eval.py`).
  Note: rationale MUST be ≥40 chars or `model_item_schema` (`minLength:40`) rejects it at L103
  before `seed_complete`.

```python
def test_track_a_scores_captured_qwen_shape_as_complete():
    """qwen/phi4 emit only the CVE in the seed + ecosystem in target; the recon-aware
    normalization must make the trial seed-complete (the hb-0vq fix)."""
    import json
    from pathlib import Path
    from llm.client import ChatResponse
    from eval import authoring_eval as ae

    captured = {"hypotheses": [{
        "program_slug": "huntr-npm-minimatch",
        "target": {"asset_type": "package", "identifier": "minimatch", "ecosystem": "npm"},
        "vuln_class": "dependency-cve",
        "source_playbook": {"vuln_class": "dependency-cve", "technique": "known-advisory-confirmation"},
        "rationale": "minimatch 3.0.4 is within the <3.0.5 range affected by CVE-2022-3517 (ReDoS).",
        "confidence": 1.0, "signals_matched": ["known advisory matches resolved version"],
        "evidence_seed": {"candidate_cve_id": "CVE-2022-3517"}}]}

    class _FakeClient:
        provider, model = "llama", "fake"
        def complete_json(self, **kw):
            return ChatResponse(text=json.dumps(captured), provider="llama", model="fake",
                                finish_reason="stop", usage={})

    recon = json.loads((Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "llm"
                        / "recon_item_minimatch.json").read_text(encoding="utf-8"))
    res = ae.score_track_a(recon, client=_FakeClient(), trials=2)
    assert res.complete == 2 and res.rate == 1.0
```

- [x] **Step 7: Run both files' suites — verify pass.**

Run: `python -m pytest tests/scripts/test_generate.py tests/scripts/test_authoring_eval.py -q`
Expected: PASS, including `test_track_a_scores_captured_qwen_shape_as_complete` (`complete == 2`).
(If `ChatResponse` construction errors, reconcile against `llm/client.py:22-28` field names.)

- [x] **Step 8: Commit.**

```bash
cd C:/Users/Garre/Workspace/sec-research
git add scripts/llm/generate.py scripts/eval/authoring_eval.py tests/scripts/test_generate.py tests/scripts/test_authoring_eval.py
git commit -m "feat(sec-research): hb-0vq recon-aware seed-field alignment (_normalize_authored, shared by prod+eval)"
```

---

### Task 2: Full-suite regression + verdict/tracker update (live re-measure = confirmation, not gating)

**Files:** run-only + `docs/superpowers/research/2026-06-30-hb-0vq-local-authoring-verdict.md` + tracker.

- [x] **Step 1: Full suite green.**

Run: `cd C:/Users/Garre/Workspace/sec-research && python -m pytest -q`
Expected: all pass (~399 baseline + 8 new), no regression — especially scope/validation/scope-match
and the supervised-driver tests.

- [x] **Step 2: Update verdict doc + tracker (done on the offline proof; live is confirmation).**

The fix is proven by the offline probe (real captured outputs, 0/6→6/6) + the eval-parity test.
Append a "Fix landed" section to the verdict doc citing the commit and the parity test. Then:
`bd -C C:/Users/Garre/.claude/harness-backlog update hb-0vq --notes "Alignment fix landed (<commit>): _normalize_authored shared by production + eval; package identity + install version now recon ground truth; cve_id alias added. Eval-parity test green. Next (follow-up bead): live Track-A re-measure + Track B."`

- [x] **Step 3: (Optional, GPU-free-permitting) live Track-A re-measure — confirmation.**

If the GPU is free: `./scripts/eval/run_matrix.ps1 -Track a -Trials 20 -ReportDir runtime/eval/2026-06-30-postfix`
then read rates. Expected: rises from 0.0 toward ~1.0, confirming the offline proof generalizes to
live output. A model still at 0 is a new datapoint to inspect (capture its raw output). This is a
**confirmation**, not a gate on "done"; if the GPU is busy, file it as a follow-up bead.

## Verification

- Unit tests pass: aliases, recon-overwrite of package identity, version stamp, version-drop-when-absent,
  candidate_cve_id preserved, non-dependency-cve untouched.
- Eval-parity test: a captured-shape output scores `complete == trials` — proving `score_track_a`
  and `generate_hypotheses` normalize identically.
- Full suite green (~399 + 8), no regression in scope/validation paths.
- Trust boundary: `candidate_cve_id` model-authored; `package_*` + `version_or_revision` recon-sourced
  (overwrite/drop); `fixed_version` unchanged; non-dependency-cve hypotheses unaffected.
- **Done =** fix committed, full suite green, verdict/tracker updated. Live re-measure is confirmation,
  not a done-gate. No eval-only fix that leaves production unchanged.

## Follow-ups (file as beads)

- **Live Track-A re-measure + Track B** (PoC-authoring through the oracle) on the now-seed-complete
  models — the end-to-end viability this fix does not itself measure.
- **Prompt hardening** (optional): instruct the model to emit the resolved version + canonical keys.
- **`score_track_a` `incomplete` bucket** — make not-seed-complete-but-non-empty trials legible.
- **Multi-advisory CVE cross-check** (pre-existing): a model `candidate_cve_id` matching a *sibling*
  advisory yields a recon-trusted but semantically-wrong `fixed_version`; not introduced here, worth a bead.

## Completion (2026-06-30)

**Landed; hb-0vq resolved.** `_normalize_authored` (shared by `generate_hypotheses` + `score_track_a`)
ships with recon-ground-truth seed identity + install version. Adversarial code review (2 agents)
added three hardening fixes, all incorporated: (1) `hypothesis-version-unresolved` ledger trace when
recon can't supply an install version (no more silent accept-but-PoC-dead); (2) the eval now requires
`fixed_version` so it models the real support gate and **rejects hallucinated CVEs**; (3) package
identity is stamp-or-drop (a model value never reaches `npm install`). A latent target-vs-seed
divergence (pin `target.identifier`) was deferred as a follow-up bead. Full suite **410 passed, 6
skipped**. Live re-measure: all four loaded models **0.00 → 1.00** (80/80 trials); gemma3-4b load-skipped.

## Retrospective

_(To be completed after execution — required by the retrospective marker.)_

- Did the eval-parity test + full suite confirm the fix without surprises?
- If the live re-measure ran: did live output generalize the offline 0→~1.0, or differ?
- Any regression from recon-overwriting package identity / dropping model version?
