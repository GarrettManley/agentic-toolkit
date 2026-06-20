# sec-research Stage 2 — Program Intake Fetchers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/fetch_program.py` — a unified CLI that fetches a bug-bounty program's scope from huntr / GHSA / IBB-H1 and emits a schema-valid `programs/<slug>/scope.yaml`, completing Stage 2 (Program Intake) of the sec-research 7-stage roadmap.

**Architecture:** A thin CLI dispatches by `--venue` to one of three fetcher modules in a new `scripts/fetchers/` package. All outbound HTTP funnels through a single `_http` chokepoint that calls the existing `policy.check_http(url, bootstrap_hosts=VENUE_BOOTSTRAP_HOSTS)` gate before any socket opens. Each venue returns a `FetchResult`; the CLI is the only component that touches the filesystem, via a shared `lib/scope_io.write_scope` / `write_draft` (extracted from `load_program.py` so both ingest paths share one validated writer).

**Tech Stack:** Python 3.14, stdlib only for HTTP (`urllib.request`, no `requests`/`bs4`), `gh` CLI for GHSA, `keyring` for H1 auth, `jsonschema` + `pyyaml` (already deps), `pytest`. Tests are fully offline via `--from-fixture`.

## Context

`sec-research/` is a hard-bounded, evidence-disciplined bug-bounty automation workspace. Stage 1 (governance: 17 hard-block hooks, JSON schemas, HMAC override signing, GHSA submission) is merged and stable with 42 passing tests; it has been dormant ~2 weeks while effort went elsewhere. Stage 1 is "the contract" — Stages 2-7 must not modify its hook contracts or schemas.

Stage 2 is the next roadmap step and the gate to everything downstream: Recon (3), Hypothesis & Test (4), Triage (5), Reporting (6) all require a **loaded program scope** to operate against, because PT-1/UPS-2 hard-block any network call or target identifier that doesn't trace to a `programs/<slug>/scope.yaml`. Today scopes are loaded only by hand (`load_program.py --from-file` / `--scaffold`). Stage 2 automates scope acquisition from the three v1 venues.

**Key de-risking finding:** the "PT-1 bootstrap problem" flagged in the Stage-2 research doc (the scope hook would block the fetcher's own HTTP *before* a scope is loaded) was **already solved** by Stage 1's `hooks/lib/policy.py::check_http(..., bootstrap_hosts=VENUE_BOOTSTRAP_HOSTS)`, which allows `huntr.com` / `api.github.com` / `api.hackerone.com` pre-scope. No `pretooluse.py` amendment is needed — Claude's PT-1 hook never sees the venue URL (the Bash command is just `python scripts/fetch_program.py …`; the HTTP happens inside the subprocess and is gated by `check_http`).

**Decisions locked during brainstorming:** all three venues (build order huntr → GHSA → IBB-H1); huntr scrapes the public page now (not scaffold-only); ecosystem inferred by probing the linked GitHub repo manifest; IBB `submission.protocol = manual-form` for Stage 2 (→ `h1-api` in Stage 7, matching the huntr precedent and Stage-1 `submit.py` reality); huntr parser stays stdlib-only.

**Tracking:** `hb-kz6` (harness-backlog beads ledger). Stage 2 of the sec-research roadmap (`docs/CHARTER.md` §Roadmap). Brainstorm research substrate: `docs/superpowers/research/2026-05-07-stage2-venue-surface.md`.

## Global Constraints

- **Working directory:** all commands run from inside `sec-research/`. Launch the implementation session with `claude` started **inside `sec-research/`** so the workspace's `.claude/settings.json` hooks resolve via `${CLAUDE_PROJECT_DIR}` (a parent-launched session runs NONE of the 17 hooks — silently).
- **Stage 1 is the contract:** do NOT modify `schema/*.json`, `hooks/pretooluse.py` (or any hook), or override mechanics. Stage 2 is additive plus one pure refactor of `load_program.py`.
- **HTTP is stdlib-only:** use `urllib.request` (mirror `hooks/lib/registry_lookup.py`). Do NOT add `requests`/`httpx`/`bs4`/`lxml` to `requirements.txt`. If the live huntr page proves un-parseable with regex+json, that is a flagged follow-up, not a silent `pip install`.
- **Every real HTTP egress is gated:** call `policy.check_http(url, bootstrap_hosts=VENUE_BOOTSTRAP_HOSTS)` BEFORE the socket opens (including before shelling out to `gh api`, synthesizing the `https://api.github.com{path}` form). `--from-fixture` mode opens no socket and skips the gate.
- **`ScopeViolation` must never be swallowed by a venue** — it carries an audit side effect (`policy-blocked` ledger entry already written). Venues catch only network/parse errors; `ScopeViolation` propagates to the CLI top level → exit 1.
- **An invalid scope must never become live:** schema-invalid or draft emits go to `scope.draft.yaml` (which the scope matcher never reads — it only loads files literally named `scope.yaml`), and `write_draft` must NOT invalidate the scope cache.
- **Slug regex:** `program_slug` must match `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (schema). The venue prefix (`huntr-`/`ghsa-`/`ibb-`) guarantees length ≥ 2.
- **TDD, frequent commits, DRY, YAGNI.** Run `pytest` before every commit. Commits stage only `sec-research/` paths (the parent-repo verify gate is skipped for sec-research-only commits; sec-research's own pre-commit hooks apply — no `findings/` touched, so no Trace-ID needed).

---

## File Structure

**Create:**
- `hooks/lib/scope_io.py` — shared scope persistence: `write_scope(slug, data, *, force=False, scaffold_aux=False) -> Path` and `write_draft(slug, data) -> Path`. Lives in `lib/` (not `scripts/`) because `scripts/` is not a package, while both scripts already do `sys.path.insert(0, HOOKS_DIR); from lib.X import Y`. No circular dep (imports `paths`, `scope_match.invalidate_scope_cache`, lazy `yaml`).
- `scripts/fetchers/__init__.py` — marks the package.
- `scripts/fetchers/_http.py` — `http_get`, `gh_api_json`, exceptions `HttpError` / `GhApiError`. The single network chokepoint.
- `scripts/fetchers/_common.py` — `FetchResult` dataclass, `slugify`, `utc_now_iso`, `infer_ecosystem_from_manifest`.
- `scripts/fetchers/huntr.py`, `scripts/fetchers/ghsa.py`, `scripts/fetchers/ibb.py` — one `fetch(...)` per venue.
- `scripts/fetch_program.py` — thin CLI dispatcher.
- `tests/scripts/test_fetch_huntr.py`, `test_fetch_ghsa.py`, `test_fetch_ibb.py`, `test_fetch_program_cli.py`, `test_fetchers_common.py`, `test_load_program_refactor.py`.
- `tests/hooks/test_scope_io.py`.
- `tests/fixtures/huntr-fetch/`, `tests/fixtures/ghsa-fetch/`, `tests/fixtures/ibb-fetch/` — canned response bodies (siblings of `huntr-test-program/`, NOT nested inside it).

**Modify:**
- `scripts/load_program.py` — replace inline write block (≈lines 119-128) + scaffold-aux writes (≈90-91) with `scope_io` calls. Pure refactor, byte-identical behavior.
- `tests/conftest.py` — add a `tmp_programs` fixture (two-target monkeypatch) and ensure `scripts/` + `hooks/` are on `sys.path`.
- `docs/SCOPE_SCHEMA.md`, `CLAUDE.md` — document the new fetcher (last task).

---

## Task 0: Extract shared scope writer (`lib/scope_io.py`)

**Files:**
- Create: `hooks/lib/scope_io.py`
- Create: `tests/hooks/test_scope_io.py`
- Create: `tests/scripts/test_load_program_refactor.py`
- Modify: `scripts/load_program.py` (write block ≈119-128; scaffold aux ≈90-91)
- Modify: `tests/conftest.py` (add `tmp_programs` fixture + sys.path inserts)

**Interfaces:**
- Produces: `write_scope(slug: str, data: dict, *, force: bool = False, scaffold_aux: bool = False) -> Path` (writes `programs/<slug>/scope.yaml`, mkdir `disclosed/`, `invalidate_scope_cache()`; raises `FileExistsError` if exists and not force; if `scaffold_aux`, also writes empty `notes.md` + `targets.txt`). `write_draft(slug: str, data: dict) -> Path` (writes `programs/<slug>/scope.draft.yaml`; does NOT invalidate cache, does NOT create `scope.yaml`).
- Consumes: `lib.paths.PROGRAMS_DIR`, `lib.scope_match.invalidate_scope_cache`.

- [ ] **Step 1: Add the `tmp_programs` fixture + sys.path to `tests/conftest.py`**

Append (and ensure the sys.path inserts exist — the `hooks/` insert is likely already present; add `scripts/` if missing):

```python
import sys
from pathlib import Path

_WS_ROOT = Path(__file__).resolve().parent.parent  # sec-research/
for _p in (_WS_ROOT / "hooks", _WS_ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest

@pytest.fixture
def tmp_programs(tmp_path, monkeypatch):
    """Redirect PROGRAMS_DIR to an isolated tmp dir for scope read/write tests.

    Two-target monkeypatch: scope_match imported PROGRAMS_DIR by name at load,
    so both modules must be patched, then the lru_cache cleared.
    """
    from lib import paths, scope_match
    test_dir = tmp_path / "programs"
    test_dir.mkdir()
    monkeypatch.setattr(paths, "PROGRAMS_DIR", test_dir)
    monkeypatch.setattr(scope_match, "PROGRAMS_DIR", test_dir)
    scope_match.invalidate_scope_cache()
    yield test_dir
    scope_match.invalidate_scope_cache()
```

- [ ] **Step 2: Write the failing tests for `scope_io`**

`tests/hooks/test_scope_io.py`:

```python
import pytest
import yaml


def _valid_min_scope(slug):
    return {
        "program_slug": slug,
        "venue": "huntr",
        "loaded_at": "2026-06-20T00:00:00Z",
        "loaded_from": "https://huntr.com/repos/acme/acme",
        "in_scope": [{"asset_type": "package", "identifier": "acme", "ecosystem": "npm"}],
        "out_of_scope": [],
        "rules": {"ai_assistance_allowed": True},
        "submission": {"protocol": "manual-form"},
    }


def test_write_scope_creates_dir_disclosed_and_invalidates_cache(tmp_programs):
    from lib import scope_io, scope_match
    data = _valid_min_scope("acme-pkg")
    path = scope_io.write_scope("acme-pkg", data)
    assert path == tmp_programs / "acme-pkg" / "scope.yaml"
    assert (tmp_programs / "acme-pkg" / "disclosed").is_dir()
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert loaded == data
    assert list(loaded.keys())[0] == "program_slug"  # sort_keys=False preserved order
    ok, prog = scope_match.is_in_scope("package", "acme")
    assert ok and prog == "acme-pkg"  # cache was invalidated -> new scope visible


def test_write_scope_refuses_existing_without_force(tmp_programs):
    from lib import scope_io
    scope_io.write_scope("acme-pkg", _valid_min_scope("acme-pkg"))
    with pytest.raises(FileExistsError):
        scope_io.write_scope("acme-pkg", _valid_min_scope("acme-pkg"))


def test_write_scope_force_overwrites(tmp_programs):
    from lib import scope_io
    scope_io.write_scope("acme-pkg", _valid_min_scope("acme-pkg"))
    d2 = _valid_min_scope("acme-pkg")
    d2["display_name"] = "changed"
    scope_io.write_scope("acme-pkg", d2, force=True)
    loaded = yaml.safe_load((tmp_programs / "acme-pkg" / "scope.yaml").read_text(encoding="utf-8"))
    assert loaded["display_name"] == "changed"


def test_write_draft_does_not_invalidate_cache_or_create_scope_yaml(tmp_programs):
    from lib import scope_io, scope_match
    p = scope_io.write_draft("bad-prog", {"program_slug": "bad-prog", "in_scope": [
        {"asset_type": "package", "identifier": "ghost"}]})
    assert p.name == "scope.draft.yaml"
    assert not (p.parent / "scope.yaml").exists()
    ok, _ = scope_match.is_in_scope("package", "ghost")
    assert ok is False  # draft is invisible to the scope matcher


def test_scaffold_aux_writes_notes_and_targets(tmp_programs):
    from lib import scope_io
    scope_io.write_scope("acme-pkg", _valid_min_scope("acme-pkg"), scaffold_aux=True)
    assert (tmp_programs / "acme-pkg" / "notes.md").exists()
    assert (tmp_programs / "acme-pkg" / "targets.txt").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/hooks/test_scope_io.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.scope_io'`.

- [ ] **Step 4: Implement `hooks/lib/scope_io.py`**

```python
"""Shared scope persistence for load_program.py and fetch_program.py.

write_scope writes the live programs/<slug>/scope.yaml and busts the scope cache.
write_draft writes programs/<slug>/scope.draft.yaml — deliberately a different
filename so the scope matcher (which only loads `scope.yaml`) never picks up an
unvalidated draft, and deliberately does NOT bust the cache.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .paths import PROGRAMS_DIR
from .scope_match import invalidate_scope_cache


def _program_dir(slug: str) -> Path:
    return PROGRAMS_DIR / slug


def write_scope(slug: str, data: dict[str, Any], *, force: bool = False,
                scaffold_aux: bool = False) -> Path:
    """Write the live scope.yaml. Raises FileExistsError if present and not force."""
    program_dir = _program_dir(slug)
    scope_path = program_dir / "scope.yaml"
    if scope_path.exists() and not force:
        raise FileExistsError(f"{scope_path} already exists; pass force=True to overwrite")
    program_dir.mkdir(parents=True, exist_ok=True)
    (program_dir / "disclosed").mkdir(exist_ok=True)
    with scope_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
    if scaffold_aux:
        notes = program_dir / "notes.md"
        if not notes.exists():
            notes.write_text(f"# Program notes: {slug}\n\n", encoding="utf-8")
        targets = program_dir / "targets.txt"
        if not targets.exists():
            targets.write_text("", encoding="utf-8")
    invalidate_scope_cache()
    return scope_path


def write_draft(slug: str, data: dict[str, Any]) -> Path:
    """Write programs/<slug>/scope.draft.yaml. Never busts the cache; never creates scope.yaml."""
    program_dir = _program_dir(slug)
    program_dir.mkdir(parents=True, exist_ok=True)
    draft_path = program_dir / "scope.draft.yaml"
    with draft_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
    return draft_path
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/hooks/test_scope_io.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Write the failing characterization test for the `load_program.py` refactor**

`tests/scripts/test_load_program_refactor.py` — proves the refactor is behavior-invisible:

```python
import sys
import subprocess
from pathlib import Path

import yaml

WS_ROOT = Path(__file__).resolve().parent.parent.parent  # sec-research/


def _run_load(args, env_programs):
    """Invoke load_program.py as a subprocess with PROGRAMS_DIR redirected via env shim."""
    cmd = [sys.executable, str(WS_ROOT / "scripts" / "load_program.py"), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=WS_ROOT,
                          env={**__import__("os").environ, "SEC_RESEARCH_PROGRAMS_DIR": str(env_programs)})


def test_from_file_writes_scope_and_disclosed_not_notes(tmp_path, monkeypatch):
    from lib import paths, scope_match, scope_io
    progs = tmp_path / "programs"; progs.mkdir()
    monkeypatch.setattr(paths, "PROGRAMS_DIR", progs)
    monkeypatch.setattr(scope_match, "PROGRAMS_DIR", progs)
    scope_match.invalidate_scope_cache()

    src = tmp_path / "scope.yaml"
    src.write_text(yaml.safe_dump({
        "program_slug": "ghsa-acme-repo", "venue": "ghsa",
        "loaded_at": "2026-06-20T00:00:00Z",
        "loaded_from": "https://github.com/acme/repo/security/advisories",
        "in_scope": [{"asset_type": "repo", "identifier": "github.com/acme/repo"}],
        "out_of_scope": [], "rules": {"ai_assistance_allowed": True},
        "submission": {"protocol": "ghsa-cli"},
    }), encoding="utf-8")

    import importlib
    lp = importlib.import_module("load_program")
    rc = lp.main_with_args(["--from-file", str(src)]) if hasattr(lp, "main_with_args") else None
    # If load_program.main() reads sys.argv, drive it that way instead:
    if rc is None:
        monkeypatch.setattr(sys, "argv", ["load_program.py", "--from-file", str(src)])
        rc = lp.main()
    assert rc == 0
    assert (progs / "ghsa-acme-repo" / "scope.yaml").exists()
    assert (progs / "ghsa-acme-repo" / "disclosed").is_dir()
    assert not (progs / "ghsa-acme-repo" / "notes.md").exists()  # --from-file never wrote notes.md
```

> Note: `load_program.py` currently reads `sys.argv` in `main()`. Drive it via `monkeypatch.setattr(sys, "argv", ...)` + `lp.main()` (the test above shows both forms; keep the `sys.argv` path). The `subprocess` helper at top is unused scaffolding — delete it if you take the in-process path.

- [ ] **Step 7: Run it to verify it fails**

Run: `python -m pytest tests/scripts/test_load_program_refactor.py -v`
Expected: FAIL (`--from-file` currently writes `notes.md`? No — it does not; it should already pass for the notes assertion but FAIL on import path until conftest sys.path lands, or pass). If it passes already, that is the characterization baseline — proceed; the point is it must still pass AFTER the refactor.

- [ ] **Step 8: Refactor `load_program.py` to use `scope_io`**

At the top imports, add: `from lib.scope_io import write_scope`.

In the `--scaffold` branch, replace the manual `program_dir.mkdir` / `disclosed` / `scope_path.write_text` / `notes.md` / `targets.txt` block with the existing-guard preserved + a single call. The scaffold writes a *template string* (not a validated dict), so keep its `write_text` of `SCAFFOLD_TEMPLATE` but route dir creation + aux files through the same shape; simplest minimal change that preserves behavior:

```python
    if args.scaffold:
        if not args.slug or not args.venue:
            print("ERROR: --scaffold requires --slug and --venue", file=sys.stderr)
            return 1
        program_dir = PROGRAMS_DIR / args.slug
        if program_dir.exists() and (program_dir / "scope.yaml").exists():
            print(f"ERROR: {program_dir / 'scope.yaml'} already exists; refusing to overwrite", file=sys.stderr)
            return 1
        program_dir.mkdir(parents=True, exist_ok=True)
        (program_dir / "disclosed").mkdir(exist_ok=True)
        scope_path = program_dir / "scope.yaml"
        scope_path.write_text(SCAFFOLD_TEMPLATE.format(
            slug=args.slug, venue=args.venue,
            loaded_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ), encoding="utf-8")
        (program_dir / "notes.md").write_text(f"# Program notes: {args.slug}\n\n", encoding="utf-8")
        (program_dir / "targets.txt").write_text("", encoding="utf-8")
        print(f"Scaffold written to: {scope_path}")
        print("Edit the file and re-run: python sec-research/scripts/load_program.py --from-file " + str(scope_path))
        return 0
```

> The `--scaffold` path writes a *template string* with placeholders that is intentionally schema-INVALID until edited, so it cannot go through `write_scope` (which receives a validated dict). Leave `--scaffold` writing the template directly (as above — unchanged). The refactor applies to the `--from-file` path only.

Replace the `--from-file` write block (≈lines 119-128) with:

```python
    slug = args.slug or data["program_slug"]
    scope_path = write_scope(slug, data, force=True)  # --from-file is explicit human intent; overwrite ok
    print(f"Program loaded: {slug}")
    print(f"  Venue: {data['venue']}")
    print(f"  In-scope: {len(data.get('in_scope', []))} entries")
    print(f"  Out-of-scope: {len(data.get('out_of_scope', []))} entries")
    print(f"  Saved to: {scope_path}")
    return 0
```

> Behavior note: the old `--from-file` path overwrote unconditionally (no exists-guard), so `force=True` preserves exact prior behavior. `invalidate_scope_cache()` is now called inside `write_scope`, so remove the now-duplicate import/call if present.

- [ ] **Step 9: Run both refactor + scope_io tests to verify they pass**

Run: `python -m pytest tests/hooks/test_scope_io.py tests/scripts/test_load_program_refactor.py -v`
Expected: PASS.

- [ ] **Step 10: Run the full suite to confirm no regressions**

Run: `python -m pytest -q`
Expected: all prior 42 tests + the new ones PASS.

- [ ] **Step 11: Commit**

```bash
git add hooks/lib/scope_io.py tests/hooks/test_scope_io.py tests/scripts/test_load_program_refactor.py scripts/load_program.py tests/conftest.py
git commit -m "refactor(scope): extract write_scope/write_draft into lib/scope_io"
```

---

## Task 1: Fetcher infrastructure (`_common.py`, `_http.py`, package)

**Files:**
- Create: `scripts/fetchers/__init__.py` (empty)
- Create: `scripts/fetchers/_common.py`
- Create: `scripts/fetchers/_http.py`
- Create: `tests/scripts/test_fetchers_common.py`

**Interfaces:**
- Produces: `FetchResult(ok: bool, slug: str, data: dict | None, draft: bool = False, warnings: list[str] = [])` (frozen dataclass). `slugify(s: str) -> str`. `utc_now_iso() -> str`. `_http.http_get(url, *, headers=None, from_fixture=None, timeout=10.0) -> str`. `_http.gh_api_json(path, *, from_fixture=None, timeout=30.0) -> dict | list`. `_http.HttpError`, `_http.GhApiError`.
- Consumes: `lib.policy.check_http`, `lib.policy.VENUE_BOOTSTRAP_HOSTS` (from Task 0's sys.path setup).

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_fetchers_common.py`:

```python
import json
import pytest


@pytest.mark.parametrize("raw,expected", [
    ("acme-org/acme-pkg", "acme-org-acme-pkg"),
    ("Acme-Org/My_Pkg.js", "acme-org-my-pkg-js"),
    ("foo.", "foo"),
    ("@scope/pkg", "scope-pkg"),
    ("a__b", "a-b"),
    ("--trim--", "trim"),
])
def test_slugify(raw, expected):
    from fetchers._common import slugify
    assert slugify(raw) == expected


def test_utc_now_iso_shape():
    from fetchers._common import utc_now_iso
    s = utc_now_iso()
    assert s.endswith("Z") and "T" in s and len(s) == 20  # 2026-06-20T12:34:56Z


def test_http_get_from_fixture_skips_network(tmp_path):
    from fetchers import _http
    fx = tmp_path / "body.html"
    fx.write_text("<html>hi</html>", encoding="utf-8")
    assert _http.http_get("https://blocked.invalid", from_fixture=fx) == "<html>hi</html>"


def test_gh_api_json_from_fixture_parses(tmp_path):
    from fetchers import _http
    fx = tmp_path / "resp.json"
    fx.write_text(json.dumps({"full_name": "a/b"}), encoding="utf-8")
    assert _http.gh_api_json("/repos/a/b", from_fixture=fx) == {"full_name": "a/b"}


def test_http_get_live_path_calls_check_http(monkeypatch):
    """Live path must invoke the scope gate before opening a socket."""
    from fetchers import _http
    calls = {}
    def fake_check(url, *, bootstrap_hosts):
        calls["url"] = url
        raise _http_scope_violation()  # simulate a block so no real socket opens
    from lib.policy import ScopeViolation
    def _http_scope_violation():
        return ScopeViolation(url="x", host="x", reason="test")
    monkeypatch.setattr(_http, "check_http", fake_check)
    with pytest.raises(ScopeViolation):
        _http.http_get("https://huntr.com/repos/a/b")
    assert calls["url"] == "https://huntr.com/repos/a/b"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_fetchers_common.py -v`
Expected: FAIL (`No module named 'fetchers'`).

- [ ] **Step 3: Implement `scripts/fetchers/__init__.py` and `_common.py`**

`scripts/fetchers/__init__.py`: empty file.

`scripts/fetchers/_common.py`:

```python
"""Shared helpers for venue scope fetchers: result type, slug + timestamp helpers,
and GitHub-manifest ecosystem inference."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fetchers import _http

# Root manifest filename -> package ecosystem (schema enum value).
_MANIFEST_ECOSYSTEM: list[tuple[str, str]] = [
    ("package.json", "npm"),
    ("pyproject.toml", "pypi"),
    ("setup.py", "pypi"),
    ("Cargo.toml", "cargo"),
    ("go.mod", "go"),
    ("pom.xml", "maven"),
    ("composer.json", "composer"),
    ("Gemfile", "rubygems"),
]


@dataclass(frozen=True)
class FetchResult:
    ok: bool
    slug: str
    data: dict | None
    draft: bool = False
    warnings: list[str] = field(default_factory=list)


def slugify(s: str) -> str:
    """Lowercase; collapse any run of non-alphanumerics to a single hyphen; strip ends."""
    s = re.sub(r"[^a-z0-9]+", "-", s.lower())
    return s.strip("-")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def infer_ecosystem_from_manifest(owner: str, repo: str, *,
                                  contents_fixture=None) -> tuple[str | None, list[str]]:
    """Probe the repo's root file listing via `gh api /repos/{o}/{r}/contents` and map a
    known manifest filename to an ecosystem. Returns (ecosystem | None, warnings)."""
    try:
        entries = _http.gh_api_json(f"/repos/{owner}/{repo}/contents", from_fixture=contents_fixture)
    except _http.GhApiError as e:
        return None, [f"ecosystem probe failed ({e}); ecosystem omitted"]
    names = {e.get("name", "") for e in entries} if isinstance(entries, list) else set()
    for fname, eco in _MANIFEST_ECOSYSTEM:
        if fname in names:
            return eco, []
    if any(n.endswith(".gemspec") for n in names):
        return "rubygems", []
    return None, ["ecosystem could not be inferred from repo manifest; omitted"]
```

- [ ] **Step 4: Implement `scripts/fetchers/_http.py`**

```python
"""HTTP egress chokepoint for venue fetchers.

Every real network call is gated by policy.check_http BEFORE the socket opens
(or before shelling out to `gh api`). --from-fixture returns canned bodies and
opens no socket, so the gate is skipped in fixture mode. ScopeViolation from the
gate propagates uncaught (it carries an audit side effect)."""
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from lib.policy import VENUE_BOOTSTRAP_HOSTS, check_http

USER_AGENT = "Garrett-Manley-SecResearch/1.0"


class HttpError(RuntimeError):
    """A live HTTP GET failed (network/timeout/HTTP-error)."""


class GhApiError(RuntimeError):
    """`gh api` exited non-zero, was not found, or returned non-JSON."""


def http_get(url: str, *, headers: dict | None = None, from_fixture=None,
             timeout: float = 10.0) -> str:
    if from_fixture is not None:
        return Path(from_fixture).read_text(encoding="utf-8")
    check_http(url, bootstrap_hosts=VENUE_BOOTSTRAP_HOSTS)  # raises ScopeViolation on block
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise HttpError(f"GET {url} -> HTTP {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise HttpError(f"GET {url} failed: {e}") from e


def gh_api_json(path: str, *, from_fixture=None, timeout: float = 30.0):
    if from_fixture is not None:
        return json.loads(Path(from_fixture).read_text(encoding="utf-8"))
    # gh hits api.github.com; gate on the synthesized URL before shelling out.
    check_http(f"https://api.github.com{path}", bootstrap_hosts=VENUE_BOOTSTRAP_HOSTS)
    try:
        proc = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise GhApiError("gh CLI not installed; install from cli.github.com")
    except subprocess.TimeoutExpired:
        raise GhApiError(f"gh api timed out after {timeout}s")
    if proc.returncode != 0:
        raise GhApiError(f"gh api failed: {proc.stderr.strip()[:500]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise GhApiError("gh api response was not JSON")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_fetchers_common.py -v`
Expected: PASS. (`_common` imports `_http` at module load; `_http` imports `lib.policy` — both resolve via conftest's sys.path inserts.)

- [ ] **Step 6: Commit**

```bash
git add scripts/fetchers/__init__.py scripts/fetchers/_common.py scripts/fetchers/_http.py tests/scripts/test_fetchers_common.py
git commit -m "feat(fetch): fetcher package scaffolding — HTTP gate + common helpers"
```

---

## Task 2: huntr fetcher

**Files:**
- Create: `scripts/fetchers/huntr.py`
- Create: `tests/scripts/test_fetch_huntr.py`
- Create: `tests/fixtures/huntr-fetch/repo_acme-org_acme-pkg.html`, `repo_no_ecosystem.html`, `repo_unknown_ecosystem.html`, `contents_npm.json`, `contents_empty.json`, `garbage.html`

**Interfaces:**
- Produces: `huntr.fetch(identifier: str, *, from_fixture=None, manifest_fixture=None) -> FetchResult`.
- Consumes: `_http.http_get`, `_common.{FetchResult, slugify, utc_now_iso, infer_ecosystem_from_manifest}`.

- [ ] **Step 1: Author the fixtures (reconcile JSON path against a real page first)**

⚠️ Before writing the parser, capture ONE real huntr repo page to confirm the embedded-JSON shape (the `__NEXT_DATA__` path below is the *expected* Next.js shape and MUST be reconciled with the actual capture). Capture is a dev action — run it yourself in a terminal, e.g. `curl -s https://huntr.com/repos/<owner>/<pkg> -o /tmp/huntr.html`, inspect the `<script id="__NEXT_DATA__">` blob, and shape the fixtures + parser keys to match. If huntr's real shape differs materially from the assumption, adjust `_parse_repo` and the fixtures together (the test asserts the *mapping*, not the raw shape).

`tests/fixtures/huntr-fetch/repo_acme-org_acme-pkg.html` (minimal, with chrome so regex extraction is exercised):

```html
<!doctype html><html><head><title>acme-pkg · huntr</title></head><body>
<div id="__next"></div>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"repo":{"owner":"acme-org","name":"acme-pkg","ecosystem":"npm","repository_url":"https://github.com/acme-org/acme-pkg","display_name":"Acme Org — acme-pkg"}}}}
</script>
</body></html>
```

`repo_no_ecosystem.html`: same but the `repo` object omits `"ecosystem"` (forces the manifest probe).
`repo_unknown_ecosystem.html`: same as `repo_no_ecosystem.html` (the probe fixture it pairs with returns no known manifest → ecosystem omitted).
`contents_npm.json`: `[{"name":"package.json","type":"file"},{"name":"README.md","type":"file"}]`
`contents_empty.json`: `[{"name":"README.md","type":"file"}]`
`garbage.html`: `<html><body>nope</body></html>`

- [ ] **Step 2: Write the failing tests**

`tests/scripts/test_fetch_huntr.py`:

```python
from pathlib import Path

from lib.schema_validate import validate_program

FX = Path(__file__).resolve().parent.parent / "fixtures" / "huntr-fetch"


def test_huntr_fixture_produces_valid_scope(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg", from_fixture=FX / "repo_acme-org_acme-pkg.html")
    assert res.ok and res.data and not res.draft
    ok, errors = validate_program(res.data)
    assert ok, errors
    assert res.data["program_slug"] == "huntr-acme-org-acme-pkg"
    assert res.data["venue"] == "huntr"
    assert res.data["venue_program_id"] == "acme-org/acme-pkg"
    assert res.data["loaded_from"] == "https://huntr.com/repos/acme-org/acme-pkg"
    assert res.data["submission"]["protocol"] == "manual-form"
    assert res.data["rules"]["ai_disclosure_required"] is True
    assert res.data["rules"]["rate_limit_per_min"] == 60
    assert "captured" in res.data["rules"]["notes"].lower()
    pkgs = [e for e in res.data["in_scope"] if e["asset_type"] == "package"]
    repos = [e for e in res.data["in_scope"] if e["asset_type"] == "repo"]
    assert pkgs[0]["ecosystem"] == "npm"
    assert repos[0]["identifier"] == "github.com/acme-org/acme-pkg"


def test_huntr_probes_manifest_when_page_silent(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg",
                      from_fixture=FX / "repo_no_ecosystem.html",
                      manifest_fixture=FX / "contents_npm.json")
    pkg = next(e for e in res.data["in_scope"] if e["asset_type"] == "package")
    assert pkg["ecosystem"] == "npm"  # inferred from package.json in contents listing


def test_huntr_ecosystem_miss_omits_field_and_warns(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/mystery",
                      from_fixture=FX / "repo_unknown_ecosystem.html",
                      manifest_fixture=FX / "contents_empty.json")
    pkg = next(e for e in res.data["in_scope"] if e["asset_type"] == "package")
    assert "ecosystem" not in pkg
    assert any("ecosystem" in w for w in res.warnings)
    ok, _ = validate_program(res.data)
    assert ok  # still schema-valid with ecosystem omitted


def test_huntr_unparseable_markup_returns_clean_error(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("acme-org/acme-pkg", from_fixture=FX / "garbage.html")
    assert res.ok is False and res.data is None
    assert any("parse" in w.lower() for w in res.warnings)


def test_huntr_bad_identifier(tmp_programs):
    from fetchers import huntr
    res = huntr.fetch("no-slash", from_fixture=FX / "repo_acme-org_acme-pkg.html")
    assert res.ok is False
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/scripts/test_fetch_huntr.py -v`
Expected: FAIL (`No module named 'fetchers.huntr'`).

- [ ] **Step 4: Implement `scripts/fetchers/huntr.py`**

```python
"""huntr.com program scope fetcher.

huntr exposes no public scope API, so we scrape the public program page
https://huntr.com/repos/<owner>/<pkg> and read its embedded __NEXT_DATA__ JSON.
Tests feed canned page bodies via from_fixture; production fetches live (gated by
_http). Ecosystem is read from the page when present, else inferred by probing the
linked GitHub repo manifest. The capture date is recorded in rules.notes."""
from __future__ import annotations

import json
import re

from fetchers import _http
from fetchers._common import (FetchResult, infer_ecosystem_from_manifest, slugify, utc_now_iso)

_NEXT_DATA_RE = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)


def _parse_repo(html: str) -> dict | None:
    """Return the repo object from the embedded JSON, or None if unparseable.
    RECONCILE these keys with a real huntr capture before trusting in production."""
    m = _NEXT_DATA_RE.search(html)
    if not m:
        return None
    try:
        blob = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None
    repo = blob.get("props", {}).get("pageProps", {}).get("repo")
    return repo if isinstance(repo, dict) else None


def fetch(identifier: str, *, from_fixture=None, manifest_fixture=None) -> FetchResult:
    if "/" not in identifier:
        return FetchResult(ok=False, slug="", data=None,
                           warnings=[f"identifier must be '<owner>/<pkg>', got {identifier!r}"])
    owner, pkg = identifier.split("/", 1)
    url = f"https://huntr.com/repos/{owner}/{pkg}"
    slug = f"huntr-{slugify(identifier)}"

    try:
        html = _http.http_get(url, from_fixture=from_fixture)
    except _http.HttpError as e:
        return FetchResult(ok=False, slug=slug, data=None, warnings=[str(e)])

    repo = _parse_repo(html)
    if repo is None:
        return FetchResult(ok=False, slug=slug, data=None,
                           warnings=["could not parse huntr page shape (no __NEXT_DATA__ repo blob)"])

    warnings: list[str] = []
    ecosystem = repo.get("ecosystem")
    # Probe the manifest only when the page is silent AND we are allowed to do live work
    # (fixture mode does no network unless an explicit manifest_fixture is supplied).
    if not ecosystem and (manifest_fixture is not None or from_fixture is None):
        ecosystem, eco_warn = infer_ecosystem_from_manifest(owner, pkg, contents_fixture=manifest_fixture)
        warnings += eco_warn
    elif not ecosystem:
        warnings.append("ecosystem not on page and probe skipped (fixture mode); omitted")

    pkg_entry: dict = {"asset_type": "package", "identifier": pkg}
    if ecosystem:
        pkg_entry["ecosystem"] = ecosystem
    pkg_entry["notes"] = "Package under huntr program scope"

    repo_id = f"github.com/{owner}/{pkg}"
    repo_entry = {"asset_type": "repo", "identifier": repo_id, "notes": "Source repo for the package"}

    scope = {
        "program_slug": slug,
        "venue": "huntr",
        "venue_program_id": identifier,
        "loaded_at": utc_now_iso(),
        "loaded_from": url,
        "display_name": repo.get("display_name", f"{owner} — {pkg}"),
        "in_scope": [pkg_entry, repo_entry],
        "out_of_scope": [],
        "rules": {
            "ai_assistance_allowed": True,
            "ai_disclosure_required": True,
            "rate_limit_per_min": 60,
            "user_agent_required": "Garrett-Manley-SecResearch/1.0 (huntr.com/research)",
            "no_dast_against_prod": True,
            "notes": f"Captured from {url} on {utc_now_iso()}.",
        },
        "submission": {"protocol": "manual-form", "endpoint": url},
    }
    return FetchResult(ok=True, slug=slug, data=scope, warnings=warnings)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_fetch_huntr.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/fetchers/huntr.py tests/scripts/test_fetch_huntr.py tests/fixtures/huntr-fetch/
git commit -m "feat(fetch): huntr scope fetcher with manifest ecosystem inference"
```

---

## Task 3: GHSA fetcher

**Files:**
- Create: `scripts/fetchers/ghsa.py`
- Create: `tests/scripts/test_fetch_ghsa.py`
- Create: `tests/fixtures/ghsa-fetch/repos_acme-org_acme-repo.json`, `security_advisories.json`

**Interfaces:**
- Produces: `ghsa.fetch(identifier: str, *, from_fixture=None, advisories_fixture=None) -> FetchResult`.
- Consumes: `_http.gh_api_json`, `_common.{FetchResult, slugify, utc_now_iso}`.

- [ ] **Step 1: Author fixtures**

`tests/fixtures/ghsa-fetch/repos_acme-org_acme-repo.json`:

```json
{"full_name":"acme-org/acme-repo","html_url":"https://github.com/acme-org/acme-repo","default_branch":"main","archived":false}
```

`tests/fixtures/ghsa-fetch/security_advisories.json`: `[]` (empty list = endpoint reachable, advisories accepted).

- [ ] **Step 2: Write the failing tests**

`tests/scripts/test_fetch_ghsa.py`:

```python
from pathlib import Path

import pytest

from lib.schema_validate import validate_program

FX = Path(__file__).resolve().parent.parent / "fixtures" / "ghsa-fetch"


def test_ghsa_fixture_produces_valid_scope(tmp_programs):
    from fetchers import ghsa
    res = ghsa.fetch("acme-org/acme-repo",
                     from_fixture=FX / "repos_acme-org_acme-repo.json",
                     advisories_fixture=FX / "security_advisories.json")
    assert res.ok
    ok, errors = validate_program(res.data)
    assert ok, errors
    assert res.data["program_slug"] == "ghsa-acme-org-acme-repo"
    assert res.data["venue"] == "ghsa"
    assert res.data["submission"]["protocol"] == "ghsa-cli"
    assert res.data["loaded_from"] == "https://github.com/acme-org/acme-repo/security/advisories"
    repos = [e for e in res.data["in_scope"] if e["asset_type"] == "repo"]
    assert repos[0]["identifier"] == "github.com/acme-org/acme-repo"
    assert all("max_payout_usd" not in e for e in res.data["in_scope"])  # GHSA has no payout


def test_ghsa_gh_error_returns_clean_failure(tmp_programs, monkeypatch):
    from fetchers import ghsa, _http
    def boom(path, **kw):
        raise _http.GhApiError("gh: not authenticated")
    monkeypatch.setattr(_http, "gh_api_json", boom)
    res = ghsa.fetch("acme-org/acme-repo")  # live path -> stubbed error
    assert res.ok is False and res.data is None
    assert any("gh" in w.lower() for w in res.warnings)


def test_ghsa_bad_identifier(tmp_programs):
    from fetchers import ghsa
    res = ghsa.fetch("noslash", from_fixture=FX / "repos_acme-org_acme-repo.json")
    assert res.ok is False
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/scripts/test_fetch_ghsa.py -v`
Expected: FAIL (`No module named 'fetchers.ghsa'`).

- [ ] **Step 4: Implement `scripts/fetchers/ghsa.py`**

```python
"""GHSA scope fetcher. Each GitHub repo is its own program (no central directory).
Uses `gh api /repos/{o}/{r}` via _http.gh_api_json (which gates on api.github.com and
reuses gh CLI auth). Probes /security-advisories to confirm advisories are accepted."""
from __future__ import annotations

from fetchers import _http
from fetchers._common import FetchResult, slugify, utc_now_iso


def fetch(identifier: str, *, from_fixture=None, advisories_fixture=None) -> FetchResult:
    if "/" not in identifier:
        return FetchResult(ok=False, slug="", data=None,
                           warnings=[f"identifier must be '<owner>/<repo>', got {identifier!r}"])
    owner, repo = identifier.split("/", 1)
    slug = f"ghsa-{slugify(identifier)}"

    try:
        _http.gh_api_json(f"/repos/{owner}/{repo}", from_fixture=from_fixture)
    except _http.GhApiError as e:
        return FetchResult(ok=False, slug=slug, data=None, warnings=[str(e)])

    warnings: list[str] = []
    adv_note = "advisory acceptance unconfirmed"
    if advisories_fixture is not None or from_fixture is None:
        try:
            _http.gh_api_json(f"/repos/{owner}/{repo}/security-advisories",
                              from_fixture=advisories_fixture)
            adv_note = "repo /security-advisories endpoint reachable (probe ok)"
        except _http.GhApiError as e:
            adv_note = f"advisory acceptance unconfirmed ({e})"
            warnings.append(adv_note)

    repo_id = f"github.com/{owner}/{repo}"
    scope = {
        "program_slug": slug,
        "venue": "ghsa",
        "venue_program_id": identifier,
        "loaded_at": utc_now_iso(),
        "loaded_from": f"https://github.com/{owner}/{repo}/security/advisories",
        "display_name": f"GHSA — {identifier}",
        "in_scope": [{"asset_type": "repo", "identifier": repo_id,
                      "notes": "GitHub repository accepting security advisories"}],
        "out_of_scope": [],
        "rules": {
            "ai_assistance_allowed": True,
            "ai_disclosure_required": True,
            "rate_limit_per_min": 60,
            "user_agent_required": "Garrett-Manley-SecResearch/1.0",
            "no_dast_against_prod": True,
            "notes": adv_note,
        },
        "submission": {"protocol": "ghsa-cli",
                       "endpoint": f"https://github.com/{owner}/{repo}/security/advisories"},
    }
    return FetchResult(ok=True, slug=slug, data=scope, warnings=warnings)
```

> Package-in-scope discovery for GHSA (inferring the package from the repo manifest) is deliberately deferred — `in_scope` carries the repo only, which satisfies the schema's `minItems: 1`. Add package inference later if Stage 3 needs it.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_fetch_ghsa.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/fetchers/ghsa.py tests/scripts/test_fetch_ghsa.py tests/fixtures/ghsa-fetch/
git commit -m "feat(fetch): GHSA scope fetcher via gh api"
```

---

## Task 4: IBB-H1 fetcher

**Files:**
- Create: `scripts/fetchers/ibb.py`
- Create: `tests/scripts/test_fetch_ibb.py`
- Create: `tests/fixtures/ibb-fetch/structured_scopes_django.json`, `forbidden_403.json`

**Interfaces:**
- Produces: `ibb.fetch(identifier: str, *, from_fixture=None, username=None) -> FetchResult`.
- Consumes: `_http.http_get`, `lib.credentials.get_credential`, `_common.{FetchResult, slugify, utc_now_iso}`.

- [ ] **Step 1: Author fixtures (reconcile shape against the real H1 API before trusting in production)**

⚠️ The H1 structured-scopes JSON shape below is a documented *assumption*; reconcile it with a real `api.hackerone.com` response (requires an H1 token) before production use. Tests assert the *mapping*, so the parser + fixture move together.

`tests/fixtures/ibb-fetch/structured_scopes_django.json` — two assets: one bounty-eligible, one VDP-only, plus embargo metadata:

```json
{"meta":{"program_handle":"ibb-python","embargo_period_days":90,"ai_assistance_allowed":true,"ai_disclosure_required":true},
 "data":[
  {"id":"1","attributes":{"asset_identifier":"django","asset_type":"OTHER","eligible_for_bounty":true,"eligible_for_submission":true}},
  {"id":"2","attributes":{"asset_identifier":"vdp-only-asset","asset_type":"OTHER","eligible_for_bounty":false,"eligible_for_submission":true}}
 ]}
```

`tests/fixtures/ibb-fetch/forbidden_403.json`: `{"errors":[{"status":403,"detail":"Reputation requirement not met."}]}`

- [ ] **Step 2: Write the failing tests**

`tests/scripts/test_fetch_ibb.py`:

```python
from pathlib import Path

from lib.schema_validate import validate_program

FX = Path(__file__).resolve().parent.parent / "fixtures" / "ibb-fetch"


def test_ibb_bounty_eligible_asset_in_scope(tmp_programs):
    from fetchers import ibb
    res = ibb.fetch("django", from_fixture=FX / "structured_scopes_django.json")
    assert res.ok and not res.draft
    ok, errors = validate_program(res.data)
    assert ok, errors
    assert res.data["program_slug"] == "ibb-django"
    assert res.data["venue"] == "ibb-h1"
    assert res.data["submission"]["protocol"] == "manual-form"  # Stage-2 stop-gap (h1-api in Stage 7)
    assert res.data["rules"]["embargo_period_days"] == 90
    in_ids = [e["identifier"] for e in res.data["in_scope"]]
    out_ids = [e["identifier"] for e in res.data["out_of_scope"]]
    assert "django" in in_ids
    assert "vdp-only-asset" not in in_ids       # VDP-only never silently in-scope
    assert "vdp-only-asset" in out_ids          # routed to out_of_scope with a reason
    assert all(e.get("reason") for e in res.data["out_of_scope"])


def test_ibb_token_denied_falls_back_to_draft(tmp_programs):
    from fetchers import ibb
    res = ibb.fetch("django", from_fixture=FX / "forbidden_403.json")
    assert res.draft is True
    assert res.data is not None  # scaffold skeleton for manual completion
    assert any("reputation" in w.lower() or "manual" in w.lower() or "denied" in w.lower()
               for w in res.warnings)
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/scripts/test_fetch_ibb.py -v`
Expected: FAIL (`No module named 'fetchers.ibb'`).

- [ ] **Step 4: Implement `scripts/fetchers/ibb.py`**

```python
"""IBB-on-HackerOne scope fetcher. IBB is one H1 program covering many OSS packages;
we fetch one program/asset per invocation. Reads are reputation-gated — on 401/403 or
a missing credential we emit a draft scaffold for manual completion rather than failing
hard. submission.protocol is manual-form for Stage 2 (h1-api arrives in Stage 7)."""
from __future__ import annotations

import json
from pathlib import Path

from fetchers import _http
from fetchers._common import FetchResult, slugify, utc_now_iso
from lib.credentials import get_credential

H1_API = "https://api.hackerone.com/v1"
DEFAULT_H1_USER = "garrettmanley"


def _is_denied(payload: dict) -> bool:
    for err in payload.get("errors", []) or []:
        if str(err.get("status")) in {"401", "403"}:
            return True
    return False


def _scaffold_draft(identifier: str, slug: str, reason: str) -> FetchResult:
    skeleton = {
        "program_slug": slug,
        "venue": "ibb-h1",
        "venue_program_id": identifier,
        "loaded_at": utc_now_iso(),
        "loaded_from": f"https://hackerone.com/ibb",
        "in_scope": [{"asset_type": "package", "identifier": identifier,
                      "notes": "PLACEHOLDER — confirm asset against H1 program scope"}],
        "out_of_scope": [],
        "rules": {"ai_assistance_allowed": True, "ai_disclosure_required": True,
                  "embargo_period_days": 90,
                  "notes": f"DRAFT scaffold ({reason}); complete manually then load via load_program.py."},
        "submission": {"protocol": "manual-form", "endpoint": "https://hackerone.com/ibb"},
    }
    return FetchResult(ok=True, slug=slug, data=skeleton, draft=True,
                       warnings=[f"IBB read denied ({reason}); emitted scope.draft.yaml for manual completion"])


def _build_from_payload(identifier: str, slug: str, payload: dict) -> FetchResult:
    if _is_denied(payload):
        return _scaffold_draft(identifier, slug, "reputation-gated (HTTP 401/403)")

    meta = payload.get("meta", {})
    in_scope, out_of_scope = [], []
    for asset in payload.get("data", []):
        attr = asset.get("attributes", {})
        aid = attr.get("asset_identifier")
        if not aid:
            continue
        if attr.get("eligible_for_bounty"):
            in_scope.append({"asset_type": "package", "identifier": aid,
                             "notes": "IBB bounty-eligible asset"})
        elif attr.get("eligible_for_submission"):
            out_of_scope.append({"asset_type": "package", "identifier": aid,
                                 "reason": "VDP-only, not bounty-eligible"})

    if not in_scope:
        return _scaffold_draft(identifier, slug, "no bounty-eligible asset found in payload")

    scope = {
        "program_slug": slug,
        "venue": "ibb-h1",
        "venue_program_id": meta.get("program_handle", identifier),
        "loaded_at": utc_now_iso(),
        "loaded_from": f"https://hackerone.com/{meta.get('program_handle', 'ibb')}",
        "display_name": f"IBB — {identifier}",
        "in_scope": in_scope,
        "out_of_scope": out_of_scope,
        "rules": {
            "ai_assistance_allowed": bool(meta.get("ai_assistance_allowed", True)),
            "ai_disclosure_required": bool(meta.get("ai_disclosure_required", True)),
            "rate_limit_per_min": 60,
            "embargo_period_days": int(meta.get("embargo_period_days", 90)),
            "notes": f"Captured from H1 structured_scopes on {utc_now_iso()}.",
        },
        "submission": {"protocol": "manual-form",
                       "endpoint": f"https://hackerone.com/{meta.get('program_handle', 'ibb')}"},
    }
    return FetchResult(ok=True, slug=slug, data=scope)


def fetch(identifier: str, *, from_fixture=None, username=None) -> FetchResult:
    slug = f"ibb-{slugify(identifier)}"

    if from_fixture is not None:
        payload = json.loads(Path(from_fixture).read_text(encoding="utf-8"))
        return _build_from_payload(identifier, slug, payload)

    # Live path: resolve H1 credential, fetch structured scopes (gated by _http).
    token = get_credential({"service": "hackerone-api", "username": username or DEFAULT_H1_USER})
    if not token:
        return _scaffold_draft(identifier, slug, "no hackerone-api credential configured")

    import base64
    auth = base64.b64encode(f"{username or DEFAULT_H1_USER}:{token}".encode()).decode()
    url = f"{H1_API}/programs/{identifier}/structured_scopes"
    try:
        body = _http.http_get(url, headers={"Authorization": f"Basic {auth}",
                                            "Accept": "application/json"})
    except _http.HttpError as e:
        msg = str(e)
        if "403" in msg or "401" in msg:
            return _scaffold_draft(identifier, slug, "reputation-gated (HTTP 401/403)")
        return FetchResult(ok=False, slug=slug, data=None, warnings=[msg])
    return _build_from_payload(identifier, slug, json.loads(body))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_fetch_ibb.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/fetchers/ibb.py tests/scripts/test_fetch_ibb.py tests/fixtures/ibb-fetch/
git commit -m "feat(fetch): IBB-H1 scope fetcher with reputation-gated draft fallback"
```

---

## Task 5: CLI dispatcher + end-to-end tests + docs

**Files:**
- Create: `scripts/fetch_program.py`
- Create: `tests/scripts/test_fetch_program_cli.py`
- Modify: `docs/SCOPE_SCHEMA.md` (§"How scopes get loaded")
- Modify: `CLAUDE.md` (Quick-commands block)

**Interfaces:**
- Produces: `fetch_program.main(argv: list[str] | None = None) -> int`.
- Consumes: `huntr.fetch`, `ghsa.fetch`, `ibb.fetch`, `lib.scope_io.{write_scope, write_draft}`, `lib.schema_validate.validate_program`, `lib.policy.ScopeViolation`.

- [ ] **Step 1: Write the failing end-to-end tests**

`tests/scripts/test_fetch_program_cli.py`:

```python
from pathlib import Path

import pytest

HUNTR_FX = Path(__file__).resolve().parent.parent / "fixtures" / "huntr-fetch" / "repo_acme-org_acme-pkg.html"


def _main(argv):
    import fetch_program
    return fetch_program.main(argv)


def test_cli_huntr_writes_scope_yaml(tmp_programs):
    rc = _main(["--venue", "huntr", "--identifier", "acme-org/acme-pkg",
                "--from-fixture", str(HUNTR_FX)])
    assert rc == 0
    assert (tmp_programs / "huntr-acme-org-acme-pkg" / "scope.yaml").exists()
    assert (tmp_programs / "huntr-acme-org-acme-pkg" / "disclosed").is_dir()


def test_cli_existing_scope_without_force_exits_1(tmp_programs):
    args = ["--venue", "huntr", "--identifier", "acme-org/acme-pkg", "--from-fixture", str(HUNTR_FX)]
    assert _main(args) == 0
    before = (tmp_programs / "huntr-acme-org-acme-pkg" / "scope.yaml").read_text(encoding="utf-8")
    assert _main(args) == 1                                  # second run, no --force
    after = (tmp_programs / "huntr-acme-org-acme-pkg" / "scope.yaml").read_text(encoding="utf-8")
    assert before == after                                  # original untouched


def test_cli_force_overwrites(tmp_programs):
    args = ["--venue", "huntr", "--identifier", "acme-org/acme-pkg", "--from-fixture", str(HUNTR_FX)]
    assert _main(args) == 0
    assert _main(args + ["--force"]) == 0


def test_cli_schema_invalid_emit_writes_draft_not_scope(tmp_programs, monkeypatch):
    """A venue that returns a schema-invalid dict must land in scope.draft.yaml, exit 1."""
    import fetch_program
    from fetchers._common import FetchResult
    bad = FetchResult(ok=True, slug="huntr-bad-prog",
                      data={"program_slug": "huntr-bad-prog"})  # missing required fields
    monkeypatch.setitem(fetch_program.FETCHERS, "huntr", lambda ident, **kw: bad)
    rc = fetch_program.main(["--venue", "huntr", "--identifier", "x/y", "--from-fixture", str(HUNTR_FX)])
    assert rc == 1
    d = tmp_programs / "huntr-bad-prog"
    assert (d / "scope.draft.yaml").exists()
    assert not (d / "scope.yaml").exists()                  # PT-1 never sees an invalid scope


def test_cli_network_failure_no_partial_write(tmp_programs, monkeypatch):
    import fetch_program
    from fetchers._common import FetchResult
    monkeypatch.setitem(fetch_program.FETCHERS, "huntr",
                        lambda ident, **kw: FetchResult(ok=False, slug="huntr-x-y", data=None,
                                                        warnings=["network down"]))
    rc = fetch_program.main(["--venue", "huntr", "--identifier", "x/y"])
    assert rc == 1
    assert not any(tmp_programs.iterdir())                  # nothing written


def test_cli_scope_violation_exits_1(tmp_programs, monkeypatch):
    import fetch_program
    from lib.policy import ScopeViolation
    def raises(ident, **kw):
        raise ScopeViolation(url="https://evil.invalid", host="evil.invalid", reason="out of scope")
    monkeypatch.setitem(fetch_program.FETCHERS, "huntr", raises)
    rc = fetch_program.main(["--venue", "huntr", "--identifier", "x/y"])
    assert rc == 1
    assert not any(tmp_programs.iterdir())
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_fetch_program_cli.py -v`
Expected: FAIL (`No module named 'fetch_program'`).

- [ ] **Step 3: Implement `scripts/fetch_program.py`**

```python
"""fetch_program.py — fetch a bug-bounty program scope from a venue and write
programs/<slug>/scope.yaml (Stage 2: Program Intake).

Usage:
    python scripts/fetch_program.py --venue huntr  --identifier <owner>/<pkg>
    python scripts/fetch_program.py --venue ghsa   --identifier <owner>/<repo>
    python scripts/fetch_program.py --venue ibb-h1 --identifier <asset>
    # tests / offline: add --from-fixture <path>; re-fetch: add --force

The fetcher's HTTP is gated by hooks/lib/policy.check_http against VENUE_BOOTSTRAP_HOSTS,
so it works before any scope is loaded (the Stage-2 bootstrap path). Schema-invalid or
draft emits go to scope.draft.yaml (never loaded into scope) and exit 1.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
HOOKS_DIR = SCRIPTS_DIR.parent / "hooks"
for _p in (str(SCRIPTS_DIR), str(HOOKS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lib.policy import ScopeViolation                      # noqa: E402
from lib.schema_validate import validate_program           # noqa: E402
from lib.scope_io import write_draft, write_scope          # noqa: E402
from fetchers import ghsa, huntr, ibb                       # noqa: E402

FETCHERS = {"huntr": huntr.fetch, "ghsa": ghsa.fetch, "ibb-h1": ibb.fetch}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch a program scope from a venue.")
    p.add_argument("--venue", required=True, choices=sorted(FETCHERS))
    p.add_argument("--identifier", required=True, help="huntr/ghsa: owner/name; ibb-h1: asset id")
    p.add_argument("--from-fixture", help="Read a canned response body instead of live HTTP (tests)")
    p.add_argument("--force", action="store_true", help="Overwrite an existing scope.yaml")
    args = p.parse_args(argv)
    fixture = Path(args.from_fixture) if args.from_fixture else None

    try:
        res = FETCHERS[args.venue](args.identifier, from_fixture=fixture)
    except ScopeViolation as e:
        print(f"ERROR (PT-1): {e}", file=sys.stderr)        # policy already logged policy-blocked
        return 1

    if not res.ok:
        for w in res.warnings:
            print(f"  - {w}", file=sys.stderr)
        print("Fetch failed; no scope written.", file=sys.stderr)
        return 1

    valid, errors = validate_program(res.data)
    if res.draft or not valid:
        path = write_draft(res.slug, res.data)
        print(f"Wrote DRAFT (NOT loaded into scope): {path}", file=sys.stderr)
        for e in errors:
            print(f"  - schema: {e}", file=sys.stderr)
        for w in res.warnings:
            print(f"  - {w}", file=sys.stderr)
        return 1

    try:
        path = write_scope(res.slug, res.data, force=args.force)
    except FileExistsError:
        print(f"ERROR: scope already exists for {res.slug}; pass --force to overwrite.", file=sys.stderr)
        return 1

    for w in res.warnings:
        print(f"  - {w}", file=sys.stderr)
    print(f"Program loaded: {res.slug}  ({len(res.data['in_scope'])} in-scope) -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the CLI tests to verify they pass**

Run: `python -m pytest tests/scripts/test_fetch_program_cli.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Update docs**

In `docs/SCOPE_SCHEMA.md`, replace the §"How scopes get loaded" Stage-2 bullet with:

```markdown
- **Stage 2** provides automated venue scope fetchers:
  `python scripts/fetch_program.py --venue <huntr|ghsa|ibb-h1> --identifier <id>`.
  - huntr: `<owner>/<pkg>` — scrapes the public program page; ecosystem inferred from the repo manifest.
  - ghsa: `<owner>/<repo>` — via `gh api`; each repo is one program.
  - ibb-h1: `<asset>` — H1 API (reputation-gated; falls back to `scope.draft.yaml` for manual completion).
  - Add `--from-fixture <path>` to parse a canned response offline; `--force` to overwrite.
  - Schema-invalid or draft emits write `scope.draft.yaml` (NEVER loaded by PT-1); complete and re-run `load_program.py --from-file`.
- **Stage 1** loads scopes manually via `scripts/load_program.py --from-file` / `--scaffold`, or by hand-writing the YAML.
```

In `CLAUDE.md`, add under the Quick-commands "Load a program scope" line:

```powershell
# Fetch a program scope automatically (Stage 2)
python scripts/fetch_program.py --venue huntr --identifier <owner>/<pkg>
python scripts/fetch_program.py --venue ghsa --identifier <owner>/<repo>
```

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: all tests PASS (42 original + ~24 new).

- [ ] **Step 7: Commit**

```bash
git add scripts/fetch_program.py tests/scripts/test_fetch_program_cli.py docs/SCOPE_SCHEMA.md CLAUDE.md
git commit -m "feat(fetch): unified fetch_program CLI + Stage-2 docs"
```

---

## Verification

**1. Full automated suite (offline):**
```bash
cd sec-research
python -m pytest -q
```
Expected: all tests green (42 original + new). No network access during tests (fixtures only).

**2. End-to-end CLI against a fixture writes a live, schema-valid scope:**
```bash
python scripts/fetch_program.py --venue huntr --identifier acme-org/acme-pkg \
  --from-fixture tests/fixtures/huntr-fetch/repo_acme-org_acme-pkg.html --force
python scripts/init_workspace.py --verify   # confirms workspace integrity
ls programs/huntr-acme-org-acme-pkg/        # scope.yaml + disclosed/ present
```
Then confirm PT-1 now accepts an in-scope target (the whole point of Stage 2):
```bash
python -c "import sys; sys.path.insert(0,'hooks'); from lib.scope_match import is_in_scope, invalidate_scope_cache; invalidate_scope_cache(); print(is_in_scope('repo','github.com/acme-org/acme-pkg'))"
```
Expected: `(True, 'huntr-acme-org-acme-pkg')`. Then delete the test program: `rm -r programs/huntr-acme-org-acme-pkg`.

**3. Invalid-emit safety:** confirm a draft never becomes live — covered by `test_cli_schema_invalid_emit_writes_draft_not_scope` and `test_write_draft_does_not_invalidate_cache_or_create_scope_yaml`. Spot-check that `scope_match.load_all_scopes()` ignores any `scope.draft.yaml`.

**4. Live smoke (OPTIONAL, user-run — needs network; do once per venue):** From inside a session launched in `sec-research/`, the `check_http` gate allows the venue bootstrap hosts, so these run without a pre-loaded scope. GHSA is the most reliable (uses your `gh auth`):
```bash
python scripts/fetch_program.py --venue ghsa --identifier <a-real-owner>/<a-real-repo>
```
Expected: `Program loaded: ghsa-<owner>-<repo> …`. Inspect the emitted `programs/<slug>/scope.yaml` for correctness, then remove it if it was only a smoke test. huntr/IBB live runs will surface any fixture-vs-reality shape drift flagged in Tasks 2 and 4 (reconcile the parser keys against the real response if they differ).

---

## Retrospective

_(Filled in after implementation via `/superpowers:plan-retrospective` or the retrospective skill.)_

**Issue state:** Closes hb-kz6 (sec-research Stage 2: Program Intake fetchers). Follow-ups discovered during implementation should be filed as new beads / `Follows up hb-kz6`.

- **What worked:**
- **Friction / surprises:**
- **Fixture-vs-reality drift** (did huntr `__NEXT_DATA__` / H1 structured-scopes shapes match the assumed fixtures? what changed?):
- **Follow-ups discovered** (e.g. GHSA package-in-scope inference, IBB `h1-api` for Stage 7, provenance.json + re-fetch/staleness checks, scope-diff alerts):
