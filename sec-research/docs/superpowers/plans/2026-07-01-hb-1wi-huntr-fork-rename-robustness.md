# Fix hb-1wi: huntr fork/rename robustness via GitHub API — Implementation Plan

> **STATUS: NOT EXECUTED — deferred after adversarial plan review, 2026-07-01.** A 9-agent
> adversarial review (before any code was written) found the premise weaker than this plan's own
> framing: `nightly.py`'s Stage 2 scope-refresh (the "multi-program/nightly huntr run" cited as
> urgency) is a literal stub with no automated caller; no multi-program huntr run is queued; zero
> observed renames of any huntr-tracked repo; and the fix as designed doesn't fully close its own
> named risk (fetch-time-only resolution misses a rename occurring after fetch but before a later
> clone, and doesn't address `scripts/fetchers/ghsa.py`'s identical, independently-confirmed bug).
> See `bd show hb-1wi`'s comment for the full disposition. This file is kept as a reusable draft
> for whoever picks this up once a real multi-program huntr run is actually queued — do not treat
> it as approved-for-execution as written.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `scripts/fetchers/huntr.py`'s repo entry carries the real, current GitHub repo identifier (following renames) instead of blindly assuming huntr's listed `<owner>/<pkg>` URL path still maps 1:1 to today's `github.com/<owner>/<pkg>`.

**Why this, why now:** Single-program runs (hb-322/minimatch) are unaffected — minimatch never renamed. This is anchor-venue robustness ahead of a multi-program/nightly huntr run, deferred from hb-dzu (commit `7cc75b4`) specifically because it wasn't needed yet. A renamed repo would silently record a stale `scope.yaml` repo identifier, which `scripts/recon/clone.py` would then try (and likely fail) to clone, or worse, actually clone a *different*, wrong repo if the stale name got reused by someone else.

**Architecture:** Add `resolve_canonical_repo(owner, repo, *, repo_fixture=None) -> tuple[str | None, list[str]]` to `scripts/fetchers/_common.py`, mirroring the file's existing `infer_ecosystem_from_manifest` function exactly (same `gh api` + `GhApiError` + `(value | None, warnings)` pattern). It calls `gh api /repos/{owner}/{repo}` — **empirically confirmed this session** to follow GitHub's rename redirects (`gh api repos/twitter/bootstrap` → `full_name: "twbs/bootstrap"`) — and returns the canonical `github.com/<full_name>`. Wire it into `huntr.py`'s `fetch()` the same way ecosystem inference is already wired in: probe live unless in pure-fixture test mode, fall back to the URL-derived default on any failure (never drop the repo entry). No other file needs to change — `clone.py`'s `_repo_url`/`_slug` only require the bare `github.com/<owner>/<repo>` string format, with no assumption tying it back to the huntr-listed owner/pkg.

**Tech Stack:** Python 3.12+, existing `fetchers._http.gh_api_json` (subprocess `gh api` wrapper, already used elsewhere in this file family), pytest, fixture-driven tests (no live network calls in the test suite itself).

## Global Constraints

- Never silently drop the repo entry — a resolution failure falls back to the current `f"github.com/{owner}/{pkg}"` construction with a warning, exactly like the ecosystem-inference failure path already does for `ecosystem`.
- Distinguish "gh api / GhApiError failure" from "response parsed but carried no `full_name`" in the warning text — two different failure shapes, mirroring `infer_ecosystem_from_manifest`'s own warning style; do not collapse them into one message.
- The new function's fixture-gating condition must mirror the existing manifest-probe condition exactly: probe live only when `repo_fixture is not None or from_fixture is None` — so existing tests that pass `from_fixture` + `manifest_fixture` but no `repo_fixture` continue to skip live-probing and keep their current, unchanged assertions.
- Test fixtures are real, trimmed captures (this session's own `gh api repos/twitter/bootstrap` — a genuine, well-known renamed repo, `full_name: "twbs/bootstrap"`), not synthetic inventions — matching this file family's established fixture convention (`contents_npm.json` etc. are already real trimmed captures).
- This repo's default branch is `master`, not `main`.
- All shell commands assume cwd is `sec-research/` unless stated otherwise.
- Existing tests must stay green: `python -m pytest tests/scripts/test_fetch_huntr.py tests/scripts/test_fetch_ghsa.py -q` and the full suite (`python -m pytest -q`).

## Out of scope (deferred, with reason)

- **Fork resolution** (walking a fork up to its `parent`/`source` upstream repo). Empirically confirmed this session (`gh api repos/kennethreitz/requests` → `full_name` unchanged, `fork: true`) that a fork does NOT redirect to its upstream — this is a separate, distinct semantic decision (should a fork's own code be scanned, or its upstream's?) that hb-1wi's own description doesn't ask for. huntr's listed repo remains the correct scan target regardless of fork status.
- **GHSA fetcher's own repo-confirmation call** (`scripts/fetchers/ghsa.py`) is unaffected — it already calls `gh api /repos/{owner}/{repo}` directly for existence confirmation (not resolution), and GHSA advisories are filed against a specific repo, not a huntr-style URL-path mapping, so this class of bug doesn't apply there.

---

## File Structure

- **Modify `scripts/fetchers/_common.py`** — add `resolve_canonical_repo(owner, repo, *, repo_fixture=None) -> tuple[str | None, list[str]]`, placed directly after `infer_ecosystem_from_manifest` (same file, same pattern).
- **Modify `scripts/fetchers/huntr.py`** — `fetch()` resolves the repo identifier via the new function before constructing `repo_entry`, using the same live-vs-fixture gating condition already used for `ecosystem`.
- **Test `tests/scripts/test_fetch_huntr.py`** — new tests for the resolved-identifier path, the unresolved-fallback path, and the GhApiError path; confirm the existing `test_huntr_live_shape_with_manifest_produces_valid_scope` assertion is unaffected.
- **Fixture `tests/fixtures/huntr-fetch/repo_twitter_bootstrap_renamed.json`** — new, trimmed real capture (`full_name` only) from this session's `gh api repos/twitter/bootstrap`.
- **Fixture `tests/fixtures/huntr-fetch/repo_no_full_name.json`** — new, a well-formed-but-unusable response (no `full_name` key) to test that edge case distinctly from a `GhApiError`.

---

## Task 1: `resolve_canonical_repo` in `scripts/fetchers/_common.py`

**Files:**
- Modify: `scripts/fetchers/_common.py`
- Test: `tests/scripts/test_fetch_huntr.py` (this repo has no dedicated `test_fetch_common.py`; `_common.py`'s existing `infer_ecosystem_from_manifest` is only tested indirectly through `huntr.py`'s own tests — confirmed via `grep -rl "infer_ecosystem_from_manifest" tests/scripts/*.py` returning nothing. Follow the same convention: test `resolve_canonical_repo` directly by importing it, in the same file as huntr.py's other tests, rather than creating a new test file for one function.)
- Create fixtures: `tests/fixtures/huntr-fetch/repo_twitter_bootstrap_renamed.json`, `tests/fixtures/huntr-fetch/repo_no_full_name.json`

**Interfaces:**
- Consumes: `fetchers._http.gh_api_json(path, *, from_fixture=None) -> dict|list`, `fetchers._http.GhApiError` (both already exist, used identically by `infer_ecosystem_from_manifest` in the same file).
- Produces: `resolve_canonical_repo(owner: str, repo: str, *, repo_fixture=None) -> tuple[str | None, list[str]]` — used by Task 2.

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/huntr-fetch/repo_twitter_bootstrap_renamed.json` with exactly:
```json
{"full_name": "twbs/bootstrap", "fork": false}
```
(This is a trimmed real capture — `gh api repos/twitter/bootstrap` genuinely returns this `full_name`, confirming GitHub's API follows the 2013 twitter→twbs org rename redirect.)

Create `tests/fixtures/huntr-fetch/repo_no_full_name.json` with exactly:
```json
{"id": 12345, "name": "bootstrap"}
```
(A well-formed JSON object that happens to carry no `full_name` key — distinct from a `GhApiError`, which is tested via monkeypatch in Task 2, not a fixture.)

- [ ] **Step 2: Write the failing tests**

Append to `tests/scripts/test_fetch_huntr.py`:

```python
def test_resolve_canonical_repo_follows_rename(tmp_programs):
    from fetchers._common import resolve_canonical_repo
    resolved, warnings = resolve_canonical_repo(
        "twitter", "bootstrap", repo_fixture=FX / "repo_twitter_bootstrap_renamed.json")
    assert resolved == "github.com/twbs/bootstrap"
    assert warnings == []


def test_resolve_canonical_repo_no_full_name_returns_none_with_warning(tmp_programs):
    from fetchers._common import resolve_canonical_repo
    resolved, warnings = resolve_canonical_repo(
        "acme-org", "acme-pkg", repo_fixture=FX / "repo_no_full_name.json")
    assert resolved is None
    assert any("full_name" in w.lower() for w in warnings)


def test_resolve_canonical_repo_gh_error_returns_none_with_warning(tmp_programs, monkeypatch):
    from fetchers import _common, _http
    def boom(path, **kw):
        raise _http.GhApiError("gh: not authenticated")
    monkeypatch.setattr(_http, "gh_api_json", boom)
    resolved, warnings = _common.resolve_canonical_repo("acme-org", "acme-pkg")
    assert resolved is None
    assert any("gh" in w.lower() for w in warnings)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd sec-research && python -m pytest tests/scripts/test_fetch_huntr.py -v -k resolve_canonical_repo`
Expected: FAIL — `ImportError: cannot import name 'resolve_canonical_repo' from 'fetchers._common'`.

- [ ] **Step 4: Implement `resolve_canonical_repo` in `scripts/fetchers/_common.py`**

Add directly after the existing `infer_ecosystem_from_manifest` function (end of file):

```python
def resolve_canonical_repo(owner: str, repo: str, *,
                           repo_fixture=None) -> tuple[str | None, list[str]]:
    """Resolve the canonical `github.com/<owner>/<repo>` via `gh api /repos/{o}/{r}` —
    GitHub's API follows rename redirects, so a pre-rename owner/repo still resolves
    and `full_name` reflects the CURRENT canonical name (confirmed empirically:
    `gh api repos/twitter/bootstrap` -> full_name "twbs/bootstrap"). Returns
    (github.com/<full_name> | None, warnings). Never raises — the caller falls back
    to its own URL-derived identifier on any failure."""
    try:
        data = _http.gh_api_json(f"/repos/{owner}/{repo}", from_fixture=repo_fixture)
    except _http.GhApiError as e:
        return None, [f"canonical repo resolution failed ({e}); using URL-derived identifier"]
    full_name = data.get("full_name") if isinstance(data, dict) else None
    if not full_name:
        return None, ["gh api repo response carried no full_name; using URL-derived identifier"]
    return f"github.com/{full_name}", []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sec-research && python -m pytest tests/scripts/test_fetch_huntr.py -v -k resolve_canonical_repo`
Expected: all 3 PASS.

- [ ] **Step 6: Commit**

```bash
cd sec-research
git add scripts/fetchers/_common.py tests/scripts/test_fetch_huntr.py tests/fixtures/huntr-fetch/repo_twitter_bootstrap_renamed.json tests/fixtures/huntr-fetch/repo_no_full_name.json
git commit -m "feat(sec-research): add resolve_canonical_repo for GitHub rename-following (hb-1wi)"
```

---

## Task 2: Wire `resolve_canonical_repo` into `scripts/fetchers/huntr.py`

**Files:**
- Modify: `scripts/fetchers/huntr.py`
- Test: `tests/scripts/test_fetch_huntr.py`

**Interfaces:**
- Consumes: `resolve_canonical_repo(owner, repo, *, repo_fixture=None) -> tuple[str | None, list[str]]` (Task 1).
- Produces: `fetch(identifier, *, from_fixture=None, manifest_fixture=None, repo_fixture=None) -> FetchResult` — new optional `repo_fixture` kwarg, additive and backward compatible (every existing call site omits it and is unaffected).

- [ ] **Step 1: Write the failing test and confirm the existing test is unaffected**

Append to `tests/scripts/test_fetch_huntr.py`:

```python
def test_huntr_resolves_renamed_repo_identifier(tmp_programs):
    """hb-1wi: a live probe that resolves to a different (renamed) canonical repo
    must be reflected in the repo entry's identifier, not the URL-derived guess."""
    from fetchers import huntr
    res = huntr.fetch("twitter/bootstrap",
                      from_fixture=FX / "repo_acme-org_acme-pkg.html",
                      manifest_fixture=FX / "contents_npm.json",
                      repo_fixture=FX / "repo_twitter_bootstrap_renamed.json")
    assert res.ok, res.warnings
    repos = [e for e in res.data["in_scope"] if e["asset_type"] == "repo"]
    assert repos[0]["identifier"] == "github.com/twbs/bootstrap"


def test_huntr_falls_back_to_url_derived_identifier_when_resolution_fails(tmp_programs):
    """A repo-resolution failure must NOT drop the repo entry — it falls back to the
    original URL-derived identifier, with a warning, exactly like ecosystem inference
    already falls back to omitting the field on failure."""
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg",
                      from_fixture=FX / "repo_acme-org_acme-pkg.html",
                      manifest_fixture=FX / "contents_npm.json",
                      repo_fixture=FX / "repo_no_full_name.json")
    assert res.ok, res.warnings
    repos = [e for e in res.data["in_scope"] if e["asset_type"] == "repo"]
    assert repos[0]["identifier"] == "github.com/acme-org/acme-pkg"
    assert any("full_name" in w.lower() for w in res.warnings)
```

Then re-run the existing test to confirm it's unaffected by the new (not-yet-implemented) code path:

Run: `cd sec-research && python -m pytest tests/scripts/test_fetch_huntr.py -v -k test_huntr_live_shape_with_manifest_produces_valid_scope`
Expected: PASS (this test passes `from_fixture` + `manifest_fixture` but no `repo_fixture` — per the gating rule in Step 2 below, this will skip live-probing once implemented and keep its current `github.com/acme-org/acme-pkg` assertion; it should already pass now since `fetch()` doesn't accept `repo_fixture` yet, so confirm this baseline before changing `fetch()`'s signature).

- [ ] **Step 2: Run the two new tests to verify they fail**

Run: `cd sec-research && python -m pytest tests/scripts/test_fetch_huntr.py -v -k "resolves_renamed or falls_back_to_url_derived"`
Expected: FAIL — `TypeError: fetch() got an unexpected keyword argument 'repo_fixture'`.

- [ ] **Step 3: Implement the wiring in `scripts/fetchers/huntr.py`**

First, add the import at the top of the file (alongside the existing `_common` import):

```python
from fetchers._common import (
    FetchResult,
    infer_ecosystem_from_manifest,
    resolve_canonical_repo,
    slugify,
    utc_now_iso,
)
```

Then change `fetch()`'s signature from:
```python
def fetch(identifier: str, *, from_fixture=None, manifest_fixture=None) -> FetchResult:
```
to:
```python
def fetch(identifier: str, *, from_fixture=None, manifest_fixture=None, repo_fixture=None) -> FetchResult:
```

Then replace the current repo-entry construction:
```python
    repo_entry: dict = {
        "asset_type": "repo",
        "identifier": f"github.com/{owner}/{pkg}",
        "notes": "Source repo for the package",
    }
```
with:
```python
    repo_identifier = f"github.com/{owner}/{pkg}"  # fallback default
    if repo_fixture is not None or from_fixture is None:
        resolved, resolve_warn = resolve_canonical_repo(owner, pkg, repo_fixture=repo_fixture)
        if resolved:
            repo_identifier = resolved
        warnings += resolve_warn
    else:
        warnings.append(
            "repo resolution skipped (fixture mode); using URL-derived identifier"
        )

    repo_entry: dict = {
        "asset_type": "repo",
        "identifier": repo_identifier,
        "notes": "Source repo for the package",
    }
```

(This sits right after the existing `pkg_entry` construction and before `now = utc_now_iso()` — place it so `warnings` is already in scope, matching where the ecosystem-probe block already appends to the same `warnings` list.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sec-research && python -m pytest tests/scripts/test_fetch_huntr.py -v`
Expected: all PASS, including the 2 new tests and every pre-existing test in the file (in particular, re-confirm `test_huntr_live_shape_with_manifest_produces_valid_scope` still asserts `github.com/acme-org/acme-pkg` unchanged — it passes no `repo_fixture`, and passes a `from_fixture`, so the gating condition `repo_fixture is not None or from_fixture is None` is `False`, skipping live-probing).

- [ ] **Step 5: Commit**

```bash
cd sec-research
git add scripts/fetchers/huntr.py tests/scripts/test_fetch_huntr.py
git commit -m "fix(sec-research): resolve renamed GitHub repos in huntr scope fetch (hb-1wi)"
```

---

## Verification

- [ ] `cd sec-research && python -m pytest -q` — full suite green, no regressions.
- [ ] `cd sec-research && python -m pytest tests/scripts/test_fetch_huntr.py -v` — every new and pre-existing test passes.
- [ ] Manual read-through: `cd sec-research && git diff master..HEAD -- scripts/` shows only `_common.py` (additive) and `huntr.py` (the repo-entry construction + signature) changed — no edits to `scripts/recon/clone.py`, `lib/scope_match.py`, or `scripts/recon_program.py` (confirms the fix is isolated at the source, matching the "no other file needs to change" architecture claim).
- [ ] Confirm hb-1wi's own description is satisfied: "Resolve the canonical source repo via the GitHub API (already a VENUE_BOOTSTRAP_HOST) before a multi-program/nightly run that can't assume URL==repo" — implemented via `resolve_canonical_repo`, gated the same way ecosystem inference already is.

## Retrospective

_(To be completed after execution via `retrospective:plan-retrospective`.)_

Tracker: `hb-1wi`.
