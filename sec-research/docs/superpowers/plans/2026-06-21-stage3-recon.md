# Stage 3 — Recon Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/recon_program.py` + the `scripts/recon/` package so that, for each in-scope asset of a loaded program scope, the workspace produces a per-asset **known-vulnerability baseline** (registry metadata + lockfile-first bounded transitive closure + shallow in-scope repo clone + OSV-batch advisory correlation), and fills the `stage_recon(scopes)` seam in the pipeline scripts.

**Architecture:** A thin CLI (`recon_program.py`) walks loaded scopes and, per in-scope asset, calls pure, fixture-injectable units in `scripts/recon/` (`metadata`, `deps`, `clone`, `advisories`), assembles a schema-valid **recon item** via `recon_item`, and writes artifacts to `runtime/recon/<slug>/`. Every network/clone egress routes through `recon/_http.py` → `policy.check_http(url, bootstrap_hosts=RECON_INFRA_HOSTS)` before the socket/subprocess opens. The CLI and the pipeline's `stage_recon()` share one entry function (`run_recon`).

**Tech Stack:** Python 3.14, stdlib only for HTTP (`urllib.request`; OSV uses a POST), `git` CLI for clone, `jsonschema` + `pyyaml` + `tomllib` (stdlib) for parsing, `pytest`. Tests are fully offline via fixture injection.

**Tracking:** `hb-ahp` (harness-backlog). Spec: `docs/superpowers/specs/2026-06-21-stage3-recon-design.md` (trace-20260621-001). Predecessor pattern: Stage 2 fetchers (`scripts/fetchers/`).

## Global Constraints

- **Working directory:** all commands run from inside `sec-research/`. Launch the implementation session with `claude` started inside `sec-research/` (native hook load) OR rely on the Workspace-root federation router; either way commits stage **only** `sec-research/` paths.
- **Stage 1 is the contract:** do NOT modify `schema/*.json` (the existing contract schemas), `hooks/policy.py`, or any hook. The recon allow-set is passed via the existing `check_http(..., bootstrap_hosts=...)` parameter — `policy.py` is untouched. New schema `schema/recon_item.schema.json` is additive (not a Stage-1 contract). The only existing files modified are the pipeline stubs `scripts/nightly.py` / `scripts/investigate.py` (filling their designed `stage_recon` seam).
- **Every egress is gated:** `recon/_http.py` calls `policy.check_http(url, bootstrap_hosts=RECON_INFRA_HOSTS)` BEFORE any socket; `clone.py` calls the same gate BEFORE the `git clone` subprocess. `--from-fixture`/injected-runner modes open no socket/subprocess and skip the gate.
- **`ScopeViolation` propagates uncaught** out of the recon units to the CLI top level → exit 1 (it carries an audit ledger side-effect). Units catch only network/parse errors.
- **No fabrication:** a missing lockfile, truncated closure, skipped clone, or failed advisory source is recorded as an explicit flag on the recon item — never silently presented as a clean/complete baseline.
- **stdlib-only HTTP:** `urllib.request` (mirror `scripts/fetchers/_http.py`). No `requests`/`httpx`/`bs4`.
- **Bounds:** closure node cap `MAX_CLOSURE_NODES = 2000`; clone size cap `CLONE_SIZE_CAP_MB = 500`.
- **v1 lockfile coverage (scoped):** one canonical lockfile per ecosystem — npm `package-lock.json`, pypi `poetry.lock`, cargo `Cargo.lock`, rubygems `Gemfile.lock`. `deps.py` uses a per-ecosystem parser registry so alternate lockfiles (yarn/pnpm/Pipfile/uv) are additive follow-ups; their absence sets `no_lockfile` and is flagged, never silently treated as zero deps.
- **TDD, frequent commits, DRY, YAGNI.** Run `pytest` before every commit. Baseline at plan start: 79 tests.

---

## File Structure

**Create:**
- `scripts/recon/__init__.py` — package marker (empty).
- `scripts/recon/_hosts.py` — `RECON_INFRA_HOSTS` frozenset.
- `scripts/recon/_http.py` — `gate`, `http_get`, `http_post_json`, `HttpError`. The egress chokepoint.
- `scripts/recon/deps.py` — `Dep`, `Closure`, `resolve_closure`, per-ecosystem lockfile parsers, `MAX_CLOSURE_NODES`.
- `scripts/recon/metadata.py` — `AssetMetadata`, `fetch_metadata`.
- `scripts/recon/clone.py` — `CloneResult`, `clone_repo`, `CLONE_SIZE_CAP_MB`.
- `scripts/recon/advisories.py` — `Advisory`, `correlate`, OSV ecosystem mapping.
- `scripts/recon/recon_item.py` — `build_recon_item`, `validate_recon_item`, `write_program_recon`.
- `scripts/recon_program.py` — `run_recon`, `main` (CLI).
- `schema/recon_item.schema.json` — JSON Schema 2020-12 for a recon item (NEW, additive).
- `tests/scripts/test_recon_http.py`, `test_recon_deps.py`, `test_recon_metadata.py`, `test_recon_clone.py`, `test_recon_advisories.py`, `test_recon_item.py`, `test_recon_program.py`.
- `tests/fixtures/recon/` — canned lockfiles, registry docs, OSV/NVD responses, a sentinel repo dir.

**Modify:**
- `scripts/nightly.py` — `stage_recon` stub → `return run_recon(scopes)`.
- `scripts/investigate.py` — same.

**Assumed available from the conftest (Stage 2):** `tests/conftest.py` already adds `scripts/` and `hooks/` to `sys.path` and provides `tmp_programs`. So `from recon import _http` and `from lib.policy import check_http, ScopeViolation` resolve in tests. **Step 1 of Task 1 verifies this; if `scripts/` is not on the path, add it there (do not duplicate).**

---

## Task 1: Egress chokepoint (`_hosts.py`, `_http.py`, package)

**Files:**
- Create: `scripts/recon/__init__.py` (empty)
- Create: `scripts/recon/_hosts.py`
- Create: `scripts/recon/_http.py`
- Create: `tests/scripts/test_recon_http.py`

**Interfaces:**
- Produces: `RECON_INFRA_HOSTS: frozenset[str]`. `gate(url: str) -> None` (raises `ScopeViolation` on block; no-op pass on allow). `http_get(url, *, headers=None, from_fixture=None, timeout=15.0) -> str`. `http_post_json(url, payload: dict, *, from_fixture=None, timeout=30.0) -> dict`. `HttpError(RuntimeError)`.
- Consumes: `lib.policy.check_http`, `lib.policy.ScopeViolation`.

- [ ] **Step 1: Confirm import paths + write the failing tests**

First confirm the conftest puts `scripts/` on `sys.path`: `python -c "import sys; sys.path.insert(0,'hooks'); sys.path.insert(0,'scripts'); import importlib"` is implicit via conftest. If `from recon import _http` fails to import in pytest with `ModuleNotFoundError: recon`, add `scripts/` to the conftest sys.path inserts (do not duplicate an existing insert).

`tests/scripts/test_recon_http.py`:

```python
import json
import pytest


def test_recon_infra_hosts_has_core_sources():
    from recon._hosts import RECON_INFRA_HOSTS
    for host in ("registry.npmjs.org", "pypi.org", "crates.io", "rubygems.org",
                 "api.github.com", "raw.githubusercontent.com", "github.com",
                 "services.nvd.nist.gov", "api.osv.dev"):
        assert host in RECON_INFRA_HOSTS


def test_http_get_from_fixture_skips_network(tmp_path):
    from recon import _http
    fx = tmp_path / "body.json"
    fx.write_text('{"ok":true}', encoding="utf-8")
    assert _http.http_get("https://blocked.invalid", from_fixture=fx) == '{"ok":true}'


def test_http_post_json_from_fixture_parses(tmp_path):
    from recon import _http
    fx = tmp_path / "resp.json"
    fx.write_text(json.dumps({"results": []}), encoding="utf-8")
    assert _http.http_post_json("https://blocked.invalid", {"queries": []}, from_fixture=fx) == {"results": []}


def test_gate_calls_check_http_with_recon_hosts(monkeypatch):
    from recon import _http
    from recon._hosts import RECON_INFRA_HOSTS
    seen = {}
    def fake_check(url, *, bootstrap_hosts):
        seen["url"] = url
        seen["hosts"] = bootstrap_hosts
    monkeypatch.setattr(_http, "check_http", fake_check)
    _http.gate("https://api.osv.dev/v1/querybatch")
    assert seen["url"] == "https://api.osv.dev/v1/querybatch"
    assert seen["hosts"] is RECON_INFRA_HOSTS


def test_http_get_live_path_gates_then_propagates_scope_violation(monkeypatch):
    from recon import _http
    from lib.policy import ScopeViolation
    def fake_check(url, *, bootstrap_hosts):
        raise ScopeViolation(url=url, host="evil.invalid", reason="test")
    monkeypatch.setattr(_http, "check_http", fake_check)
    with pytest.raises(ScopeViolation):
        _http.http_get("https://evil.invalid/x")  # live path: no fixture
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_recon_http.py -v`
Expected: FAIL (`No module named 'recon'`).

- [ ] **Step 3: Implement `_hosts.py`**

`scripts/recon/__init__.py`: empty file.

`scripts/recon/_hosts.py`:

```python
"""Recon data-source hosts, treated as trust-establishing infrastructure (same
category as policy.VENUE_BOOTSTRAP_HOSTS) and allowed once any scope is loaded.
Passed to policy.check_http via bootstrap_hosts; Stage-1 policy.py is not edited."""
from __future__ import annotations

RECON_INFRA_HOSTS: frozenset[str] = frozenset({
    # package registries
    "registry.npmjs.org", "pypi.org", "crates.io", "rubygems.org",
    # github (metadata, raw manifests, clone)
    "api.github.com", "raw.githubusercontent.com", "github.com",
    # advisory databases
    "services.nvd.nist.gov", "api.osv.dev",
})
```

- [ ] **Step 4: Implement `_http.py`**

```python
"""HTTP egress chokepoint for recon. Every live call is gated by policy.check_http
against RECON_INFRA_HOSTS BEFORE the socket opens. from_fixture returns canned
bodies and opens no socket (gate skipped). ScopeViolation propagates uncaught."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from lib.policy import check_http
from recon._hosts import RECON_INFRA_HOSTS

USER_AGENT = "Garrett-Manley-SecResearch/1.0 (recon)"


class HttpError(RuntimeError):
    """A live HTTP call failed (network/timeout/HTTP-error)."""


def gate(url: str) -> None:
    """Raise ScopeViolation if url's host is not in scope or RECON_INFRA_HOSTS."""
    check_http(url, bootstrap_hosts=RECON_INFRA_HOSTS)


def http_get(url: str, *, headers: dict | None = None, from_fixture=None,
             timeout: float = 15.0) -> str:
    if from_fixture is not None:
        return Path(from_fixture).read_text(encoding="utf-8")
    gate(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise HttpError(f"GET {url} -> HTTP {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise HttpError(f"GET {url} failed: {e}") from e


def http_post_json(url: str, payload: dict, *, from_fixture=None,
                   timeout: float = 30.0) -> dict:
    if from_fixture is not None:
        return json.loads(Path(from_fixture).read_text(encoding="utf-8"))
    gate(url)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HttpError(f"POST {url} -> HTTP {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise HttpError(f"POST {url} failed: {e}") from e
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_recon_http.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/recon/__init__.py scripts/recon/_hosts.py scripts/recon/_http.py tests/scripts/test_recon_http.py
git commit -m "feat(recon): egress chokepoint — RECON_INFRA_HOSTS + gated _http"
```

---

## Task 2: Dependency closure (`deps.py`)

**Files:**
- Create: `scripts/recon/deps.py`
- Create: `tests/scripts/test_recon_deps.py`
- Create: `tests/fixtures/recon/deps/` (lockfile fixtures, written inline by tests)

**Interfaces:**
- Produces: `Dep(name: str, version: str, ecosystem: str)` (frozen). `Closure(direct: list[Dep], deps: list[Dep], lockfile: str | None, no_lockfile: bool, truncated: bool, total_before_cap: int)`. `resolve_closure(source_dir: Path, ecosystem: str) -> Closure`. `infer_ecosystem(source_dir: Path) -> str | None`. `MAX_CLOSURE_NODES = 2000`.
- Consumes: nothing external (pure filesystem parsing; `tomllib`, `json`, `re`).

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_recon_deps.py`:

```python
import json
from pathlib import Path


def _write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_npm_package_lock_v3_closure(tmp_path):
    from recon.deps import resolve_closure
    _write(tmp_path / "package-lock.json", json.dumps({
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "root", "version": "1.0.0"},
            "node_modules/lodash": {"version": "4.17.21"},
            "node_modules/ms": {"version": "2.1.3"},
        },
    }))
    c = resolve_closure(tmp_path, "npm")
    assert c.no_lockfile is False and c.lockfile == "package-lock.json"
    names = {(d.name, d.version) for d in c.deps}
    assert ("lodash", "4.17.21") in names and ("ms", "2.1.3") in names
    assert all(d.ecosystem == "npm" for d in c.deps)
    assert ("root", "1.0.0") not in names  # the "" root package is excluded


def test_cargo_lock_closure(tmp_path):
    from recon.deps import resolve_closure
    _write(tmp_path / "Cargo.lock",
           '[[package]]\nname = "serde"\nversion = "1.0.197"\n\n'
           '[[package]]\nname = "libc"\nversion = "0.2.153"\n')
    c = resolve_closure(tmp_path, "cargo")
    names = {(d.name, d.version) for d in c.deps}
    assert ("serde", "1.0.197") in names and ("libc", "0.2.153") in names


def test_poetry_lock_closure(tmp_path):
    from recon.deps import resolve_closure
    _write(tmp_path / "poetry.lock",
           '[[package]]\nname = "requests"\nversion = "2.31.0"\n\n'
           '[[package]]\nname = "urllib3"\nversion = "2.2.1"\n')
    c = resolve_closure(tmp_path, "pypi")
    names = {(d.name, d.version) for d in c.deps}
    assert ("requests", "2.31.0") in names and ("urllib3", "2.2.1") in names


def test_gemfile_lock_closure(tmp_path):
    from recon.deps import resolve_closure
    _write(tmp_path / "Gemfile.lock",
           "GEM\n  remote: https://rubygems.org/\n  specs:\n"
           "    rack (3.0.9)\n    rake (13.1.0)\n\nPLATFORMS\n  ruby\n")
    c = resolve_closure(tmp_path, "rubygems")
    names = {(d.name, d.version) for d in c.deps}
    assert ("rack", "3.0.9") in names and ("rake", "13.1.0") in names


def test_no_lockfile_sets_flag_and_empty_closure(tmp_path):
    from recon.deps import resolve_closure
    c = resolve_closure(tmp_path, "npm")  # empty dir
    assert c.no_lockfile is True and c.lockfile is None and c.deps == []


def test_closure_is_capped(tmp_path, monkeypatch):
    import recon.deps as deps
    monkeypatch.setattr(deps, "MAX_CLOSURE_NODES", 2)
    pkgs = {"": {"name": "root", "version": "1"}}
    for i in range(5):
        pkgs[f"node_modules/p{i}"] = {"version": f"0.0.{i}"}
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": pkgs}), encoding="utf-8")
    c = deps.resolve_closure(tmp_path, "npm")
    assert c.truncated is True and len(c.deps) == 2 and c.total_before_cap == 5


def test_infer_ecosystem_from_present_lockfile(tmp_path):
    from recon.deps import infer_ecosystem
    assert infer_ecosystem(tmp_path) is None
    (tmp_path / "Cargo.lock").write_text("", encoding="utf-8")
    assert infer_ecosystem(tmp_path) == "cargo"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_recon_deps.py -v`
Expected: FAIL (`No module named 'recon.deps'`).

- [ ] **Step 3: Implement `deps.py`**

```python
"""Lockfile-first transitive dependency closure resolution (bounded).

One canonical lockfile per ecosystem in v1; the _PARSERS registry makes
alternate lockfiles (yarn/pnpm/Pipfile/uv) additive. A missing lockfile yields
an empty closure with no_lockfile=True (never silently treated as zero deps).
The closure is capped at MAX_CLOSURE_NODES with truncated=True + total_before_cap."""
from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

MAX_CLOSURE_NODES = 2000


@dataclass(frozen=True)
class Dep:
    name: str
    version: str
    ecosystem: str


@dataclass
class Closure:
    direct: list[Dep] = field(default_factory=list)
    deps: list[Dep] = field(default_factory=list)
    lockfile: str | None = None
    no_lockfile: bool = False
    truncated: bool = False
    total_before_cap: int = 0


def _parse_package_lock(path: Path, ecosystem: str) -> list[Dep]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[Dep] = []
    for key, meta in (data.get("packages") or {}).items():
        if key == "":  # the root project, not a dependency
            continue
        name = meta.get("name") or key.split("node_modules/")[-1]
        version = meta.get("version")
        if name and version:
            out.append(Dep(name=name, version=version, ecosystem=ecosystem))
    # lockfileVersion 1 fallback: "dependencies" map
    if not out:
        for name, meta in (data.get("dependencies") or {}).items():
            v = meta.get("version") if isinstance(meta, dict) else None
            if name and v:
                out.append(Dep(name=name, version=v, ecosystem=ecosystem))
    return out


def _parse_toml_packages(path: Path, ecosystem: str) -> list[Dep]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    out: list[Dep] = []
    for pkg in data.get("package", []) or []:
        name, version = pkg.get("name"), pkg.get("version")
        if name and version:
            out.append(Dep(name=name, version=version, ecosystem=ecosystem))
    return out


_GEMSPEC_RE = re.compile(r"^    ([A-Za-z0-9_.\-]+) \(([^()]+)\)$")


def _parse_gemfile_lock(path: Path, ecosystem: str) -> list[Dep]:
    out: list[Dep] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _GEMSPEC_RE.match(line)
        if m:
            out.append(Dep(name=m.group(1), version=m.group(2), ecosystem=ecosystem))
    return out


# ecosystem -> (lockfile filename, parser). One canonical lockfile per ecosystem in v1.
_PARSERS: dict[str, tuple[str, Callable[[Path, str], list[Dep]]]] = {
    "npm": ("package-lock.json", _parse_package_lock),
    "pypi": ("poetry.lock", _parse_toml_packages),
    "cargo": ("Cargo.lock", _parse_toml_packages),
    "rubygems": ("Gemfile.lock", _parse_gemfile_lock),
}


def resolve_closure(source_dir: Path, ecosystem: str) -> Closure:
    spec = _PARSERS.get(ecosystem)
    if spec is None:
        return Closure(no_lockfile=True)
    filename, parser = spec
    lock_path = source_dir / filename
    if not lock_path.exists():
        return Closure(no_lockfile=True)
    deps = parser(lock_path, ecosystem)
    total = len(deps)
    truncated = total > MAX_CLOSURE_NODES
    capped = deps[:MAX_CLOSURE_NODES] if truncated else deps
    return Closure(direct=capped, deps=capped, lockfile=filename,
                   no_lockfile=False, truncated=truncated, total_before_cap=total)


def infer_ecosystem(source_dir: Path) -> str | None:
    """Infer the ecosystem from which canonical lockfile is present in source_dir.
    Lets repo assets that carry no `ecosystem` field (e.g. GHSA-sourced repos) still
    get a closure. Returns None if no recognized lockfile is present."""
    for eco, (filename, _) in _PARSERS.items():
        if (source_dir / filename).exists():
            return eco
    return None
```

> Note: v1 treats the parsed lockfile set as both `direct` and `deps` (the full pinned tree). Distinguishing direct-vs-transitive within a lockfile is a follow-up; the recon item carries both fields so the distinction can be refined without a schema change.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_recon_deps.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/recon/deps.py tests/scripts/test_recon_deps.py
git commit -m "feat(recon): lockfile-first bounded dependency closure"
```

---

## Task 3: Registry metadata (`metadata.py`)

**Files:**
- Create: `scripts/recon/metadata.py`
- Create: `tests/scripts/test_recon_metadata.py`

**Interfaces:**
- Produces: `AssetMetadata(identifier, ecosystem, latest: str | None, versions: list[str], repo_url: str | None, maintainers: list[str])` (frozen). `fetch_metadata(identifier: str, ecosystem: str, *, from_fixture=None) -> AssetMetadata`.
- Consumes: `recon._http.http_get`.

> Design note: metadata is fetched via the gated `recon/_http` directly (offline-testable, self-contained). `hooks/lib/registry_lookup.py` already caches version lists; routing through its cache is a follow-up optimization, not required for v1.

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_recon_metadata.py`:

```python
import json
from pathlib import Path

FX = Path(__file__).resolve().parent.parent / "fixtures" / "recon"


def _write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def test_npm_metadata_parses_repo_and_versions(tmp_path):
    from recon.metadata import fetch_metadata
    fx = tmp_path / "npm.json"
    _write(fx, {
        "dist-tags": {"latest": "4.2.1"},
        "versions": {"4.2.0": {}, "4.2.1": {}},
        "repository": {"url": "git+https://github.com/acme-org/acme.git"},
        "maintainers": [{"name": "alice"}, {"name": "bob"}],
    })
    m = fetch_metadata("acme", "npm", from_fixture=fx)
    assert m.latest == "4.2.1"
    assert set(m.versions) == {"4.2.0", "4.2.1"}
    assert m.repo_url == "github.com/acme-org/acme"
    assert m.maintainers == ["alice", "bob"]


def test_pypi_metadata_parses(tmp_path):
    from recon.metadata import fetch_metadata
    fx = tmp_path / "pypi.json"
    _write(fx, {
        "info": {"version": "2.31.0",
                 "project_urls": {"Source": "https://github.com/psf/requests"}},
        "releases": {"2.30.0": [], "2.31.0": []},
    })
    m = fetch_metadata("requests", "pypi", from_fixture=fx)
    assert m.latest == "2.31.0"
    assert m.repo_url == "github.com/psf/requests"
    assert set(m.versions) == {"2.30.0", "2.31.0"}


def test_metadata_missing_repo_is_none(tmp_path):
    from recon.metadata import fetch_metadata
    fx = tmp_path / "npm.json"
    _write(fx, {"dist-tags": {"latest": "1.0.0"}, "versions": {"1.0.0": {}}})
    m = fetch_metadata("noredir", "npm", from_fixture=fx)
    assert m.repo_url is None and m.latest == "1.0.0"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_recon_metadata.py -v`
Expected: FAIL (`No module named 'recon.metadata'`).

- [ ] **Step 3: Implement `metadata.py`**

```python
"""Per-asset registry metadata: latest, versions, repo link, maintainers.
Fetched via the gated recon/_http (offline-testable). Repo URLs are normalized
to the bare `github.com/<owner>/<repo>` identifier used elsewhere in the workspace."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from recon import _http

_REGISTRY_URL = {
    "npm": "https://registry.npmjs.org/{id}",
    "pypi": "https://pypi.org/pypi/{id}/json",
    "cargo": "https://crates.io/api/v1/crates/{id}",
    "rubygems": "https://rubygems.org/api/v1/gems/{id}.json",
}

_GH_RE = re.compile(r"github\.com[/:]([^/]+)/([^/.\s]+)")


@dataclass(frozen=True)
class AssetMetadata:
    identifier: str
    ecosystem: str
    latest: str | None = None
    versions: list[str] = field(default_factory=list)
    repo_url: str | None = None
    maintainers: list[str] = field(default_factory=list)


def _normalize_repo(raw: str | None) -> str | None:
    if not raw:
        return None
    m = _GH_RE.search(raw)
    return f"github.com/{m.group(1)}/{m.group(2)}" if m else None


def _gather_repo_candidate(doc: dict, ecosystem: str) -> str | None:
    if ecosystem == "npm":
        repo = doc.get("repository")
        return repo.get("url") if isinstance(repo, dict) else (repo if isinstance(repo, str) else None)
    if ecosystem == "pypi":
        urls = (doc.get("info") or {}).get("project_urls") or {}
        for v in urls.values():
            if "github.com" in (v or ""):
                return v
        return (doc.get("info") or {}).get("home_page")
    if ecosystem == "cargo":
        return (doc.get("crate") or {}).get("repository")
    if ecosystem == "rubygems":
        return doc.get("source_code_uri") or doc.get("homepage_uri")
    return None


def fetch_metadata(identifier: str, ecosystem: str, *, from_fixture=None) -> AssetMetadata:
    url = _REGISTRY_URL[ecosystem].format(id=identifier)
    doc = json.loads(_http.http_get(url, from_fixture=from_fixture))

    if ecosystem == "npm":
        latest = (doc.get("dist-tags") or {}).get("latest")
        versions = sorted((doc.get("versions") or {}).keys())
        maintainers = [m.get("name") for m in (doc.get("maintainers") or []) if m.get("name")]
    elif ecosystem == "pypi":
        latest = (doc.get("info") or {}).get("version")
        versions = sorted((doc.get("releases") or {}).keys())
        maintainers = []
    elif ecosystem == "cargo":
        crate = doc.get("crate") or {}
        latest = crate.get("newest_version") or crate.get("max_version")
        versions = sorted(v.get("num") for v in (doc.get("versions") or []) if v.get("num"))
        maintainers = []
    else:  # rubygems
        latest = doc.get("version")
        versions = []  # rubygems gem endpoint returns latest only; versions via a follow-up
        maintainers = []

    return AssetMetadata(
        identifier=identifier, ecosystem=ecosystem, latest=latest,
        versions=versions, repo_url=_normalize_repo(_gather_repo_candidate(doc, ecosystem)),
        maintainers=maintainers,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_recon_metadata.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/recon/metadata.py tests/scripts/test_recon_metadata.py
git commit -m "feat(recon): registry metadata fetch + repo normalization"
```

---

## Task 4: Gated shallow clone (`clone.py`)

**Files:**
- Create: `scripts/recon/clone.py`
- Create: `tests/scripts/test_recon_clone.py`

**Interfaces:**
- Produces: `CloneResult(cloned: bool, clone_path: str | None, commit_sha: str | None, skipped_reason: str | None)` (frozen). `clone_repo(repo_identifier: str, dest_root: Path, *, runner=subprocess.run, from_fixture=None) -> CloneResult`. `CLONE_SIZE_CAP_MB = 500`.
- Consumes: `recon._http.gate`.

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_recon_clone.py`:

```python
import subprocess
from pathlib import Path


class _FakeProc:
    def __init__(self, stdout="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


def test_clone_gates_then_runs_and_captures_sha(tmp_path, monkeypatch):
    from recon import clone as clonemod
    gated = {}
    monkeypatch.setattr(clonemod, "gate", lambda url: gated.setdefault("url", url))
    calls = []
    def runner(cmd, **kw):
        calls.append(cmd)
        if cmd[:2] == ["git", "clone"]:
            Path(cmd[-1]).mkdir(parents=True, exist_ok=True)
            return _FakeProc()
        if "rev-parse" in cmd:
            return _FakeProc(stdout="abc123\n")
        return _FakeProc()
    r = clonemod.clone_repo("github.com/acme-org/acme", tmp_path, runner=runner)
    assert r.cloned is True and r.commit_sha == "abc123"
    assert r.clone_path.endswith("acme-org-acme")
    assert gated["url"] == "https://github.com/acme-org/acme"  # gate fired on the clone URL
    assert calls[0][:2] == ["git", "clone"]


def test_clone_failure_sets_skipped_reason(tmp_path, monkeypatch):
    from recon import clone as clonemod
    monkeypatch.setattr(clonemod, "gate", lambda url: None)
    def runner(cmd, **kw):
        if cmd[:2] == ["git", "clone"]:
            return _FakeProc(returncode=1)
        return _FakeProc()
    r = clonemod.clone_repo("github.com/acme-org/acme", tmp_path, runner=runner)
    assert r.cloned is False and r.skipped_reason and "clone" in r.skipped_reason.lower()


def test_clone_scope_violation_propagates(tmp_path, monkeypatch):
    from recon import clone as clonemod
    from lib.policy import ScopeViolation
    def boom(url):
        raise ScopeViolation(url=url, host="github.com", reason="test")
    monkeypatch.setattr(clonemod, "gate", boom)
    import pytest
    with pytest.raises(ScopeViolation):
        clonemod.clone_repo("github.com/acme-org/acme", tmp_path, runner=lambda *a, **k: _FakeProc())
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_recon_clone.py -v`
Expected: FAIL (`No module named 'recon.clone'`).

- [ ] **Step 3: Implement `clone.py`**

```python
"""Gated shallow clone of an in-scope repo. gate(url) fires BEFORE the git
subprocess (the subprocess-scope-gap mitigation). Only in-scope repos are cloned;
dependency source is not. Clone/size failures set skipped_reason and recon continues."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from recon._http import gate

CLONE_SIZE_CAP_MB = 500


@dataclass(frozen=True)
class CloneResult:
    cloned: bool
    clone_path: str | None = None
    commit_sha: str | None = None
    skipped_reason: str | None = None


def _dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def _repo_url(repo_identifier: str) -> str:
    # repo_identifier is the bare "github.com/<owner>/<repo>" form used in scopes.
    return f"https://{repo_identifier}" if not repo_identifier.startswith("http") else repo_identifier


def _slug(repo_identifier: str) -> str:
    parts = repo_identifier.rstrip("/").split("/")
    return f"{parts[-2]}-{parts[-1]}" if len(parts) >= 2 else parts[-1]


def clone_repo(repo_identifier: str, dest_root: Path, *,
               runner=subprocess.run, from_fixture=None) -> CloneResult:
    dest = dest_root / _slug(repo_identifier)
    url = _repo_url(repo_identifier)
    gate(url)  # raises ScopeViolation if blocked — propagates uncaught

    dest_root.mkdir(parents=True, exist_ok=True)
    proc = runner(["git", "clone", "--depth", "1", url, str(dest)],
                  capture_output=True, text=True)
    if getattr(proc, "returncode", 1) != 0:
        return CloneResult(cloned=False,
                           skipped_reason=f"clone failed: {getattr(proc, 'stderr', '')[:200]}".strip())

    if _dir_size_mb(dest) > CLONE_SIZE_CAP_MB:
        return CloneResult(cloned=False, clone_path=str(dest),
                           skipped_reason=f"size>{CLONE_SIZE_CAP_MB}MB cap")

    sha_proc = runner(["git", "-C", str(dest), "rev-parse", "HEAD"],
                      capture_output=True, text=True)
    sha = (getattr(sha_proc, "stdout", "") or "").strip() or None
    return CloneResult(cloned=True, clone_path=str(dest), commit_sha=sha)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_recon_clone.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/recon/clone.py tests/scripts/test_recon_clone.py
git commit -m "feat(recon): gated shallow clone with size cap + SHA capture"
```

---

## Task 5: Advisory correlation (`advisories.py`)

**Files:**
- Create: `scripts/recon/advisories.py`
- Create: `tests/scripts/test_recon_advisories.py`

**Interfaces:**
- Produces: `Advisory(id, cve: str | None, source: str, severity: str | None, affected_range: str | None, fixed: str | None, package: str)` (frozen). `correlate(deps: list[Dep], disclosed_dir: Path, *, osv_batch_fixture=None, osv_detail_fixtures: dict | None = None) -> tuple[list[Advisory], list[str]]`.
- Consumes: `recon._http.http_post_json`, `recon._http.http_get`, `recon.deps.Dep`.

OSV usage: POST `https://api.osv.dev/v1/querybatch` with `{"queries":[{"package":{"name","ecosystem"},"version"}...]}` → results aligned by index, each `{"vulns":[{"id"}...]}`. Then GET `https://api.osv.dev/v1/vulns/{id}` per unique id for detail. Map ecosystem enum → OSV name: npm→`npm`, pypi→`PyPI`, cargo→`crates.io`, rubygems→`RubyGems`.

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_recon_advisories.py`:

```python
import json
from pathlib import Path

from recon.deps import Dep


def test_osv_batch_maps_to_advisories(tmp_path):
    from recon.advisories import correlate
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({"results": [
        {"vulns": [{"id": "GHSA-xxxx"}]},
        {},  # second dep: no vulns
    ]}), encoding="utf-8")
    detail = {
        "GHSA-xxxx": {
            "id": "GHSA-xxxx", "aliases": ["CVE-2024-1234"],
            "severity": [{"type": "CVSS_V3", "score": "7.5"}],
            "affected": [{"package": {"name": "acme"},
                          "ranges": [{"events": [{"introduced": "0"}, {"fixed": "4.2.0"}]}]}],
        }
    }
    deps = [Dep("acme", "4.1.0", "npm"), Dep("ms", "2.1.3", "npm")]
    advs, errors = correlate(deps, tmp_path / "disclosed",
                             osv_batch_fixture=batch, osv_detail_fixtures=detail)
    assert errors == []
    a = next(x for x in advs if x.id == "GHSA-xxxx")
    assert a.cve == "CVE-2024-1234" and a.source == "osv"
    assert a.severity == "7.5" and a.fixed == "4.2.0" and a.package == "acme"


def test_disclosed_reports_are_folded_in(tmp_path):
    from recon.advisories import correlate
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({"results": [{}]}), encoding="utf-8")
    disclosed = tmp_path / "disclosed"
    disclosed.mkdir()
    (disclosed / "GHSA-yyyy.json").write_text(
        json.dumps({"id": "GHSA-yyyy", "package": "acme", "severity": "low"}), encoding="utf-8")
    advs, errors = correlate([Dep("acme", "1.0.0", "npm")], disclosed,
                             osv_batch_fixture=batch, osv_detail_fixtures={})
    assert any(a.id == "GHSA-yyyy" and a.source == "disclosed" for a in advs)


def test_osv_source_error_is_flagged_not_fatal(tmp_path, monkeypatch):
    from recon import advisories as adv
    def boom(url, payload, **kw):
        raise adv._http.HttpError("osv down")
    monkeypatch.setattr(adv._http, "http_post_json", boom)
    advs, errors = adv.correlate([Dep("acme", "1.0.0", "npm")], tmp_path / "disclosed")
    assert advs == [] and any("osv" in e for e in errors)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_recon_advisories.py -v`
Expected: FAIL (`No module named 'recon.advisories'`).

- [ ] **Step 3: Implement `advisories.py`**

```python
"""Advisory correlation over a dependency closure.

OSV batch query is the correlation engine (aggregates GHSA/PyPA/RustSec/npm/Go);
per-id detail fetches enrich severity/range/fixed. programs/<slug>/disclosed/
records are folded in as venue-known items. A source erroring is flagged (not
fatal) so the baseline records exactly where it is incomplete."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from recon import _http
from recon.deps import Dep

_OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
_OSV_VULN_URL = "https://api.osv.dev/v1/vulns/{id}"
_OSV_ECOSYSTEM = {"npm": "npm", "pypi": "PyPI", "cargo": "crates.io", "rubygems": "RubyGems"}


@dataclass(frozen=True)
class Advisory:
    id: str
    cve: str | None
    source: str
    severity: str | None
    affected_range: str | None
    fixed: str | None
    package: str


def _detail_to_advisory(detail: dict, package: str) -> Advisory:
    cve = next((a for a in detail.get("aliases", []) if a.startswith("CVE-")), None)
    sev = None
    for s in detail.get("severity", []) or []:
        if s.get("score"):
            sev = s["score"]
            break
    affected_range = fixed = None
    for aff in detail.get("affected", []) or []:
        if aff.get("package", {}).get("name") in (package, None):
            for rng in aff.get("ranges", []) or []:
                for ev in rng.get("events", []) or []:
                    if "fixed" in ev:
                        fixed = ev["fixed"]
                        affected_range = f"<{fixed}"
            break
    return Advisory(id=detail.get("id", ""), cve=cve, source="osv",
                    severity=sev, affected_range=affected_range, fixed=fixed, package=package)


def _load_disclosed(disclosed_dir: Path) -> list[Advisory]:
    out: list[Advisory] = []
    if not disclosed_dir.is_dir():
        return out
    for f in sorted(disclosed_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        out.append(Advisory(id=d.get("id", f.stem), cve=d.get("cve"), source="disclosed",
                            severity=d.get("severity"), affected_range=d.get("affected_range"),
                            fixed=d.get("fixed"), package=d.get("package", "")))
    return out


def correlate(deps: list[Dep], disclosed_dir: Path, *,
              osv_batch_fixture=None, osv_detail_fixtures: dict | None = None) -> tuple[list[Advisory], list[str]]:
    errors: list[str] = []
    advisories: list[Advisory] = []

    queries = [{"package": {"name": d.name, "ecosystem": _OSV_ECOSYSTEM.get(d.ecosystem, d.ecosystem)},
                "version": d.version} for d in deps]
    try:
        batch = _http.http_post_json(_OSV_BATCH_URL, {"queries": queries},
                                     from_fixture=osv_batch_fixture)
        results = batch.get("results", [])
        for dep, res in zip(deps, results):
            for vuln in (res or {}).get("vulns", []) or []:
                vid = vuln.get("id")
                if not vid:
                    continue
                if osv_detail_fixtures is not None:
                    detail = osv_detail_fixtures.get(vid, {"id": vid})
                else:
                    detail = json.loads(_http.http_get(_OSV_VULN_URL.format(id=vid)))
                advisories.append(_detail_to_advisory(detail, dep.name))
    except _http.HttpError as e:
        errors.append(f"osv: {e}")

    advisories.extend(_load_disclosed(disclosed_dir))
    return advisories, errors
```

> NVD enrichment (CVSS for advisories whose `severity` is None but carry a CVE) is a thin follow-up via the same `_http` gate; OSV detail already supplies CVSS in v1, so it is not on the critical path. If added, it sets an `advisory_source_error:nvd` flag on failure, identical to the OSV pattern.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_recon_advisories.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/recon/advisories.py tests/scripts/test_recon_advisories.py
git commit -m "feat(recon): OSV-batch advisory correlation + disclosed fold-in"
```

---

## Task 6: Recon item assembly + schema (`recon_item.py`, `schema/recon_item.schema.json`)

**Files:**
- Create: `schema/recon_item.schema.json`
- Create: `scripts/recon/recon_item.py`
- Create: `tests/scripts/test_recon_item.py`

**Interfaces:**
- Consumes: `recon.metadata.AssetMetadata`, `recon.deps.Closure`/`Dep`, `recon.clone.CloneResult`, `recon.advisories.Advisory`.
- Produces: `build_recon_item(slug, asset: dict, metadata: AssetMetadata | None, closure: Closure, clone_result: CloneResult | None, advisories: list[Advisory], extra_flags: list[str], *, ts: str) -> dict`. `validate_recon_item(item: dict) -> tuple[bool, list[str]]`. `write_program_recon(slug, items: list[dict], closures: dict[str, Closure], recon_root: Path) -> Path`.

- [ ] **Step 1: Create the schema**

`schema/recon_item.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Recon Item",
  "type": "object",
  "additionalProperties": false,
  "required": ["slug", "asset", "transitive_closure", "known_advisories", "flags", "recon_ts"],
  "properties": {
    "slug": {"type": "string"},
    "asset": {
      "type": "object", "additionalProperties": false, "required": ["asset_type", "identifier"],
      "properties": {
        "asset_type": {"type": "string"},
        "identifier": {"type": "string"},
        "ecosystem": {"type": ["string", "null"]}
      }
    },
    "resolved_version": {"type": ["string", "null"]},
    "repo": {
      "type": ["object", "null"], "additionalProperties": false,
      "properties": {
        "identifier": {"type": ["string", "null"]},
        "clone_path": {"type": ["string", "null"]},
        "commit_sha": {"type": ["string", "null"]},
        "cloned": {"type": "boolean"}
      }
    },
    "direct_deps": {"type": "array", "items": {"type": "object"}},
    "transitive_closure": {
      "type": "object", "additionalProperties": false, "required": ["count", "truncated"],
      "properties": {
        "count": {"type": "integer"},
        "truncated": {"type": "boolean"},
        "path": {"type": ["string", "null"]}
      }
    },
    "known_advisories": {"type": "array", "items": {"type": "object"}},
    "flags": {"type": "array", "items": {"type": "string"}},
    "recon_ts": {"type": "string"}
  }
}
```

- [ ] **Step 2: Write the failing tests**

`tests/scripts/test_recon_item.py`:

```python
from pathlib import Path

from recon.deps import Closure, Dep
from recon.metadata import AssetMetadata
from recon.clone import CloneResult
from recon.advisories import Advisory


def _closure():
    return Closure(direct=[Dep("lodash", "4.17.21", "npm")],
                   deps=[Dep("lodash", "4.17.21", "npm")],
                   lockfile="package-lock.json", no_lockfile=False,
                   truncated=False, total_before_cap=1)


def test_build_and_validate_recon_item():
    from recon.recon_item import build_recon_item, validate_recon_item
    item = build_recon_item(
        "huntr-acme", {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"},
        AssetMetadata("acme", "npm", latest="4.2.1", repo_url="github.com/acme-org/acme"),
        _closure(),
        CloneResult(cloned=True, clone_path="runtime/recon/huntr-acme/source/acme-org-acme",
                    commit_sha="abc"),
        [Advisory("GHSA-x", "CVE-2024-1", "osv", "7.5", "<4.2.0", "4.2.0", "acme")],
        extra_flags=[], ts="2026-06-21T00:00:00Z")
    ok, errors = validate_recon_item(item)
    assert ok, errors
    assert item["resolved_version"] == "4.2.1"
    assert item["repo"]["cloned"] is True
    assert item["transitive_closure"]["count"] == 1
    assert item["known_advisories"][0]["id"] == "GHSA-x"


def test_flags_propagate_from_closure_and_clone():
    from recon.recon_item import build_recon_item
    c = Closure(no_lockfile=True)
    item = build_recon_item(
        "s", {"asset_type": "package", "identifier": "x", "ecosystem": "npm"},
        None, c,
        CloneResult(cloned=False, skipped_reason="size>500MB cap"),
        [], extra_flags=["advisory_source_error:osv"], ts="2026-06-21T00:00:00Z")
    assert "no_lockfile" in item["flags"]
    assert any(f.startswith("clone_skipped") for f in item["flags"])
    assert "advisory_source_error:osv" in item["flags"]


def test_write_program_recon_emits_json_and_closure(tmp_path):
    from recon.recon_item import build_recon_item, write_program_recon
    item = build_recon_item("s", {"asset_type": "package", "identifier": "x", "ecosystem": "npm"},
                            None, _closure(), None, [], extra_flags=[], ts="2026-06-21T00:00:00Z")
    out = write_program_recon("s", [item], {"x": _closure()}, tmp_path)
    assert (tmp_path / "s" / "recon.json").exists()
    assert (tmp_path / "s" / "dep-graph" / "x.closure.jsonl").exists()
    assert out == tmp_path / "s" / "recon.json"
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/scripts/test_recon_item.py -v`
Expected: FAIL (`No module named 'recon.recon_item'`).

- [ ] **Step 4: Implement `recon_item.py`**

```python
"""Assemble, validate, and persist per-asset recon items (the Stage 4 contract).

build_recon_item derives flags from the closure (no_lockfile / closure_truncated)
and clone (clone_skipped:*) plus any extra_flags (e.g. advisory_source_error:*).
write_program_recon persists recon.json + per-asset closure jsonl under
runtime/recon/<slug>/."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "recon_item.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _closure_path(slug: str, asset_id: str) -> str:
    return f"runtime/recon/{slug}/dep-graph/{asset_id}.closure.jsonl"


def build_recon_item(slug, asset, metadata, closure, clone_result, advisories,
                     extra_flags, *, ts):
    flags = list(extra_flags)
    if closure.no_lockfile:
        flags.append("no_lockfile")
    if closure.truncated:
        flags.append("closure_truncated")
    repo = None
    if clone_result is not None:
        if not clone_result.cloned and clone_result.skipped_reason:
            flags.append(f"clone_skipped:{clone_result.skipped_reason}")
        repo = {
            "identifier": (metadata.repo_url if metadata else None),
            "clone_path": clone_result.clone_path,
            "commit_sha": clone_result.commit_sha,
            "cloned": clone_result.cloned,
        }
    return {
        "slug": slug,
        "asset": {"asset_type": asset["asset_type"], "identifier": asset["identifier"],
                  "ecosystem": asset.get("ecosystem")},
        "resolved_version": (metadata.latest if metadata else None),
        "repo": repo,
        "direct_deps": [asdict(d) for d in closure.direct],
        "transitive_closure": {
            "count": len(closure.deps),
            "truncated": closure.truncated,
            "path": _closure_path(slug, asset["identifier"]) if closure.deps else None,
        },
        "known_advisories": [asdict(a) for a in advisories],
        "flags": flags,
        "recon_ts": ts,
    }


def validate_recon_item(item: dict) -> tuple[bool, list[str]]:
    validator = jsonschema.Draft202012Validator(_SCHEMA)
    errors = [e.message for e in validator.iter_errors(item)]
    return (not errors), errors


def write_program_recon(slug, items, closures, recon_root: Path) -> Path:
    prog_dir = recon_root / slug
    (prog_dir / "dep-graph").mkdir(parents=True, exist_ok=True)
    for asset_id, closure in closures.items():
        if not closure.deps:
            continue
        lines = "\n".join(json.dumps(asdict(d)) for d in closure.deps)
        (prog_dir / "dep-graph" / f"{asset_id}.closure.jsonl").write_text(
            lines + "\n", encoding="utf-8")
    recon_json = prog_dir / "recon.json"
    recon_json.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return recon_json
```

> `asdict` on `Dep`/`Advisory` frozen dataclasses yields plain dicts that satisfy the schema's `items: {type: object}`. The schema deliberately keeps `known_advisories`/`direct_deps` item shapes loose so advisory/dep fields can evolve without a Stage-1-style contract churn.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_recon_item.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add schema/recon_item.schema.json scripts/recon/recon_item.py tests/scripts/test_recon_item.py
git commit -m "feat(recon): recon-item assembly, schema, and artifact writer"
```

---

## Task 7: Orchestrator CLI + pipeline wiring (`recon_program.py`)

**Files:**
- Create: `scripts/recon_program.py`
- Create: `tests/scripts/test_recon_program.py`
- Modify: `scripts/nightly.py` (`stage_recon`), `scripts/investigate.py` (`stage_recon`)

**Interfaces:**
- Produces: `run_recon(scopes: dict, *, recon_root: Path | None = None, ts: str | None = None) -> list[dict]`. `main(argv: list[str] | None = None) -> int`.
- Consumes: all `recon.*` units; `lib.scope_match.load_all_scopes`; `lib.policy.ScopeViolation`; `lib.paths.WORKSPACE_ROOT`.

- [ ] **Step 1: Write the failing end-to-end tests**

`tests/scripts/test_recon_program.py`:

```python
from pathlib import Path


def _scope(slug, asset):
    return {slug: {"program_slug": slug, "venue": "huntr", "in_scope": [asset],
                   "out_of_scope": []}}


def test_run_recon_produces_item_per_in_scope_asset(tmp_path, monkeypatch):
    import recon_program as rp
    from recon.metadata import AssetMetadata
    from recon.deps import Closure, Dep
    from recon.clone import CloneResult

    monkeypatch.setattr(rp.metadata, "fetch_metadata",
                        lambda ident, eco, **kw: AssetMetadata(ident, eco, latest="1.0.0",
                                                               repo_url="github.com/acme/acme"))
    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda repo, dest, **kw: CloneResult(cloned=True, clone_path=str(dest),
                                                             commit_sha="sha1"))
    monkeypatch.setattr(rp.deps, "resolve_closure",
                        lambda src, eco: Closure(direct=[Dep("d", "1", eco)], deps=[Dep("d", "1", eco)],
                                                 lockfile="package-lock.json", total_before_cap=1))
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))

    scopes = _scope("huntr-acme", {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="2026-06-21T00:00:00Z")
    assert len(items) == 1 and items[0]["asset"]["identifier"] == "acme"
    assert (tmp_path / "huntr-acme" / "recon.json").exists()


def test_run_recon_skips_non_package_repo_assets(tmp_path, monkeypatch):
    import recon_program as rp
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))
    scopes = _scope("s", {"asset_type": "url", "identifier": "https://x.example"})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="t")
    assert items == []  # v1 handles only package/repo


def test_run_recon_isolates_per_asset_failure(tmp_path, monkeypatch):
    import recon_program as rp
    def boom(ident, eco, **kw):
        raise RuntimeError("registry exploded")
    monkeypatch.setattr(rp.metadata, "fetch_metadata", boom)
    monkeypatch.setattr(rp.deps, "resolve_closure",
                        lambda src, eco: __import__("recon.deps", fromlist=["Closure"]).Closure(no_lockfile=True))
    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda *a, **k: __import__("recon.clone", fromlist=["CloneResult"]).CloneResult(cloned=False, skipped_reason="x"))
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))
    scopes = _scope("s", {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="t")
    assert len(items) == 1 and any("recon_error" in f for f in items[0]["flags"])


def test_main_all_returns_zero(tmp_path, monkeypatch):
    import recon_program as rp
    monkeypatch.setattr(rp, "load_all_scopes", lambda: {})
    assert rp.main(["--all"]) == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_recon_program.py -v`
Expected: FAIL (`No module named 'recon_program'`).

- [ ] **Step 3: Implement `recon_program.py`**

```python
"""recon_program.py — Stage 3 Recon Module orchestrator.

Usage:
    python scripts/recon_program.py --slug <slug>
    python scripts/recon_program.py --all
    # tests drive run_recon() directly with monkeypatched units.

For each in-scope package/repo asset of each (selected) loaded scope, assemble a
recon item and write artifacts to runtime/recon/<slug>/. Egress is gated inside
the recon units (RECON_INFRA_HOSTS via policy.check_http). ScopeViolation
propagates to exit 1."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
HOOKS_DIR = SCRIPTS_DIR.parent / "hooks"
for _p in (str(SCRIPTS_DIR), str(HOOKS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lib.policy import ScopeViolation                       # noqa: E402
from lib.scope_match import load_all_scopes                 # noqa: E402
from lib.paths import WORKSPACE_ROOT                        # noqa: E402
from recon import advisories, clone, deps, metadata         # noqa: E402
from recon.recon_item import build_recon_item, write_program_recon  # noqa: E402

_RECON_ASSET_TYPES = {"package", "repo"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recon_one_asset(slug, asset, disclosed_dir, source_root, ts):
    """Returns (item, closure) or raises ScopeViolation. Other errors → recon_error flag."""
    extra_flags: list[str] = []
    md = clone_res = None
    closure = deps.Closure(no_lockfile=True)
    try:
        eco = asset.get("ecosystem")
        if asset["asset_type"] == "package" and eco:
            md = metadata.fetch_metadata(asset["identifier"], eco)
        repo_id = md.repo_url if md else (asset["identifier"] if asset["asset_type"] == "repo" else None)
        if repo_id:
            clone_res = clone.clone_repo(repo_id, source_root)
            if clone_res.cloned and clone_res.clone_path:
                # repo assets may carry no ecosystem (e.g. GHSA) — infer from the clone.
                eco = eco or deps.infer_ecosystem(Path(clone_res.clone_path))
                if eco:
                    closure = deps.resolve_closure(Path(clone_res.clone_path), eco)
        advs, adv_errors = advisories.correlate(closure.deps, disclosed_dir)
        extra_flags += [f"advisory_source_error:{e.split(':')[0]}" for e in adv_errors]
    except ScopeViolation:
        raise
    except Exception as e:  # per-asset isolation (C: one bad asset doesn't sink the run)
        extra_flags.append(f"recon_error:{type(e).__name__}")
        advs = []
    item = build_recon_item(slug, asset, md, closure, clone_res, advs, extra_flags, ts=ts)
    return item, closure


def run_recon(scopes: dict, *, recon_root: Path | None = None, ts: str | None = None) -> list[dict]:
    recon_root = recon_root or (WORKSPACE_ROOT / "runtime" / "recon")
    ts = ts or _utc_now_iso()
    all_items: list[dict] = []
    for slug, scope in scopes.items():
        disclosed_dir = WORKSPACE_ROOT / "programs" / slug / "disclosed"
        source_root = recon_root / slug / "source"
        items, closures = [], {}
        for asset in scope.get("in_scope", []):
            if asset.get("asset_type") not in _RECON_ASSET_TYPES:
                continue
            item, closure = _recon_one_asset(slug, asset, disclosed_dir, source_root, ts)
            items.append(item)
            closures[asset["identifier"]] = closure
        if items:
            write_program_recon(slug, items, closures, recon_root)
        all_items.extend(items)
    return all_items


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 3 recon over loaded program scopes.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--slug", help="Run recon for a single loaded program slug")
    g.add_argument("--all", action="store_true", help="Run recon for every loaded scope")
    args = p.parse_args(argv)

    scopes = load_all_scopes()
    if args.slug:
        scopes = {args.slug: scopes[args.slug]} if args.slug in scopes else {}
        if not scopes:
            print(f"ERROR: no loaded scope for slug {args.slug!r}", file=sys.stderr)
            return 1
    try:
        items = run_recon(scopes)
    except ScopeViolation as e:
        print(f"ERROR (PT-1): {e}", file=sys.stderr)
        return 1
    print(f"Recon complete: {len(items)} asset(s) across {len(scopes)} program(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the CLI tests to verify they pass**

Run: `python -m pytest tests/scripts/test_recon_program.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Wire the pipeline stubs**

In `scripts/nightly.py`, replace the `stage_recon` stub body with a call into the orchestrator (read the file first to match its import style; add the import near the top):

```python
from recon_program import run_recon  # near other scripts imports

def stage_recon(scopes: dict) -> list[dict]:
    return run_recon(scopes)
```

Apply the identical change in `scripts/investigate.py`.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: all tests PASS (79 baseline + new recon tests).

- [ ] **Step 7: Commit**

```bash
git add scripts/recon_program.py tests/scripts/test_recon_program.py scripts/nightly.py scripts/investigate.py
git commit -m "feat(recon): orchestrator CLI + stage_recon pipeline wiring"
```

---

## Verification

**1. Full offline suite:**
```bash
cd sec-research
python -m pytest -q
```
Expected: all green (79 baseline + ~24 recon tests). No network during tests (fixtures/monkeypatch only).

**2. CLI smoke against a loaded fixture scope (offline-ish):** load a tiny in-scope npm package scope, then:
```bash
python scripts/recon_program.py --slug <loaded-slug>
ls runtime/recon/<loaded-slug>/        # recon.json + dep-graph/ present
python -c "import json; d=json.load(open('runtime/recon/<loaded-slug>/recon.json')); print(d[0]['flags'], d[0]['transitive_closure'])"
```
Expected: one recon item per in-scope asset; `recon.json` validates against `schema/recon_item.schema.json`.

**3. Gate verification:** confirm `recon/_http.gate` and `clone.clone_repo` call `policy.check_http` before any socket/subprocess — covered by `test_recon_http.py::test_gate_calls_check_http_with_recon_hosts`, `test_http_get_live_path_gates_then_propagates_scope_violation`, and `test_recon_clone.py::test_clone_gates_then_runs_and_captures_sha` / `test_clone_scope_violation_propagates`.

**4. Optional live smoke (user-run, needs network; one in-scope program):** from inside a `sec-research/` session, `python scripts/recon_program.py --slug <real-slug>` — registry/OSV/clone hosts are allowed by `RECON_INFRA_HOSTS`. Inspect `runtime/recon/<slug>/recon.json`; reconcile any registry/OSV field-shape drift against reality (the recon analogue of Stage 2's fixture-vs-reality follow-up).

---

## Retrospective

**Issue state:** Closes hb-ahp (sec-research Stage 3: Recon Module). Follows up hb-kz6. Follow-ups discovered during implementation should be filed as new beads (`Follows up hb-ahp`) — likely candidates: alternate lockfile parsers (yarn/pnpm/Pipfile/uv), NVD CVSS enrichment (v1 leans on OSV-detail CVSS), direct-vs-transitive dep distinction, registry_lookup cache routing, rubygems version list, repo-asset **published-package identification** (v1 resolves a repo's dependency closure via lockfile-presence inference but does not yet identify the package(s) the repo itself publishes — partial coverage of spec R2), live registry/OSV field-shape reconciliation.

- **What worked:**
- **Friction / surprises:**
- **Fixture-vs-reality drift** (did npm/pypi/cargo/rubygems registry docs + OSV batch/detail shapes match the assumed fixtures? what changed?):
- **Follow-ups discovered:**
