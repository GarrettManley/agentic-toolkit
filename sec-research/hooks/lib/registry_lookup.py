"""Package-version validation against ecosystem registries, with file cache.

Cache: runtime/cache/registry/<ecosystem>/<package>.json (1h TTL).
Supports: npm, pypi, cargo, rubygems. Others raise NotImplementedError per-ecosystem.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .paths import RUNTIME_CACHE_REGISTRY_DIR

CACHE_TTL_SECONDS = 3600  # 1 hour

# pkg@version pattern (greedy on package name to support scoped packages like @scope/pkg)
# Also matches simple `lodash@4.17.21` form.
PKG_VERSION_RE = re.compile(r"\b(@?[a-zA-Z0-9][a-zA-Z0-9._/-]+)@(\d+\.[\w.+-]+)\b")


def extract_pkg_versions(text: str) -> list[tuple[str, str]]:
    """Extract (package_name, version) tuples from text. Ecosystem must be inferred separately."""
    return [(m.group(1), m.group(2)) for m in PKG_VERSION_RE.finditer(text)]


def _cache_path(ecosystem: str, package: str) -> Path:
    safe_pkg = package.replace("/", "__").replace("@", "_at_")
    return RUNTIME_CACHE_REGISTRY_DIR / ecosystem / f"{safe_pkg}.json"


def _load_cache(ecosystem: str, package: str) -> dict[str, Any] | None:
    p = _cache_path(ecosystem, package)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if (time.time() - data.get("_cached_at", 0)) > CACHE_TTL_SECONDS:
            return None
        return data
    except Exception:
        return None


def _save_cache(ecosystem: str, package: str, data: dict[str, Any]) -> None:
    p = _cache_path(ecosystem, package)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {**data, "_cached_at": time.time()}
    try:
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _query_npm(package: str) -> list[str] | None:
    try:
        import urllib.request
        url = f"https://registry.npmjs.org/{package}"
        with urllib.request.urlopen(url, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return list(data.get("versions", {}).keys())
    except Exception:
        return None


def _query_pypi(package: str) -> list[str] | None:
    try:
        import urllib.request
        url = f"https://pypi.org/pypi/{package}/json"
        with urllib.request.urlopen(url, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return list(data.get("releases", {}).keys())
    except Exception:
        return None


def _query_cargo(package: str) -> list[str] | None:
    try:
        import urllib.request
        url = f"https://crates.io/api/v1/crates/{package}"
        req = urllib.request.Request(url, headers={"User-Agent": "sec-research/1.0"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [v["num"] for v in data.get("versions", []) or []]
    except Exception:
        return None


def _query_rubygems(package: str) -> list[str] | None:
    try:
        import urllib.request
        url = f"https://rubygems.org/api/v1/versions/{package}.json"
        with urllib.request.urlopen(url, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [v["number"] for v in data]
    except Exception:
        return None


_QUERIERS = {
    "npm": _query_npm,
    "pypi": _query_pypi,
    "cargo": _query_cargo,
    "rubygems": _query_rubygems,
}


def list_versions(ecosystem: str, package: str) -> list[str] | None:
    """List known versions for a package. None if registry unreachable."""
    cached = _load_cache(ecosystem, package)
    if cached is not None and "versions" in cached:
        return cached["versions"]

    querier = _QUERIERS.get(ecosystem)
    if querier is None:
        raise NotImplementedError(f"registry not supported in Stage 1: {ecosystem}")

    versions = querier(package)
    if versions is not None:
        _save_cache(ecosystem, package, {"versions": versions})
    return versions


def version_exists(ecosystem: str, package: str, version: str) -> tuple[bool, str | None]:
    """Check (package@version) exists in the ecosystem registry."""
    versions = list_versions(ecosystem, package)
    if versions is None:
        return False, f"{ecosystem} registry unreachable; could not confirm {package}@{version}"
    if version not in versions:
        return False, f"version {version} not found in {ecosystem} registry for {package}"
    return True, None
