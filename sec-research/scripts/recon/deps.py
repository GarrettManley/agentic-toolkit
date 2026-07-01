"""Lockfile-first transitive dependency closure resolution (bounded).

One canonical lockfile per ecosystem in v1; the _PARSERS registry makes
alternate lockfiles (yarn/pnpm/Pipfile/uv) additive. A missing lockfile yields
an empty closure with no_lockfile=True (never silently treated as zero deps).
The closure is capped at MAX_CLOSURE_NODES with truncated=True + total_before_cap.

v1 does not distinguish direct from transitive deps; `direct` is always empty
(requires manifest parsing — a follow-up); `deps` is the full pinned lockfile
closure."""
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
    # v1: `direct` is always [] — distinguishing direct from transitive requires
    # manifest parsing, which is a follow-up. `deps` is the full pinned closure.
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
            # Platform-qualified gems append `-<platform>` to the version string
            # (e.g. "1.16.3-x86_64-linux"). Ruby canonical versions never contain
            # `-`; strip the suffix to get the advisory-matchable version.
            raw_version = m.group(2)
            version = raw_version.split("-", 1)[0]
            out.append(Dep(name=m.group(1), version=version, ecosystem=ecosystem))
    return out


# ecosystem -> (lockfile filename, parser). One canonical lockfile per ecosystem in v1.
_PARSERS: dict[str, tuple[str, Callable[[Path, str], list[Dep]]]] = {
    "npm": ("package-lock.json", _parse_package_lock),
    "pypi": ("poetry.lock", _parse_toml_packages),
    "cargo": ("Cargo.lock", _parse_toml_packages),
    "rubygems": ("Gemfile.lock", _parse_gemfile_lock),
}


def resolve_closure(source_dir: Path, ecosystem: str) -> Closure:
    """Return the full pinned lockfile closure for *ecosystem* under *source_dir*.

    v1 does not distinguish direct from transitive deps — `direct` is always []
    (requires manifest parsing, which is a follow-up task). `deps` is the full
    pinned closure, capped at MAX_CLOSURE_NODES.
    """
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
    return Closure(direct=[], deps=capped, lockfile=filename,
                   no_lockfile=False, truncated=truncated, total_before_cap=total)


def infer_ecosystem(source_dir: Path) -> str | None:
    """Infer the ecosystem from which canonical lockfile is present in source_dir.
    Lets repo assets that carry no `ecosystem` field (e.g. GHSA-sourced repos) still
    get a closure. Returns None if no recognized lockfile is present."""
    for eco, (filename, _) in _PARSERS.items():
        if (source_dir / filename).exists():
            return eco
    return None


def _read_npm_name(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    name = data.get("name") if isinstance(data, dict) else None
    return name if isinstance(name, str) and name else None


def infer_package_name(source_dir: Path, ecosystem: str) -> str | None:
    """Resolve the real registry package name from *ecosystem*'s manifest under
    *source_dir*. v1: npm only (package.json's "name" field) — cargo/pypi/rubygems
    are deferred (see docs/superpowers/plans/2026-07-01-hb-7hf-*.md Out of scope).
    Returns None on a missing manifest, parse failure, missing name field, or any
    non-npm ecosystem — never guesses from the directory/repo name."""
    if ecosystem != "npm":
        return None
    manifest = source_dir / "package.json"
    if not manifest.exists():
        return None
    return _read_npm_name(manifest)
