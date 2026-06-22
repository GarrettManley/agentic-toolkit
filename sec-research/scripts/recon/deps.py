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
