"""Match a target identifier (URL, host, package, repo) against loaded program scopes.

Loaded scopes live in programs/<slug>/scope.yaml. This module loads and caches
all currently-loaded scopes and provides a scoped match function.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .paths import PROGRAMS_DIR


def _yaml_load(path: Path) -> dict[str, Any]:
    """Lightweight YAML loader (PyYAML if available; minimal fallback otherwise)."""
    try:
        import yaml
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Minimal fallback for single-program tests; supports the canonical scope.yaml format
        return _minimal_yaml_parse(path.read_text(encoding="utf-8"))


def _minimal_yaml_parse(text: str) -> dict[str, Any]:
    """Extremely minimal YAML parser for scope.yaml when PyYAML isn't installed.

    Recommend installing PyYAML for production use. This fallback handles the
    canonical scope.yaml shape only.
    """
    raise NotImplementedError(
        "PyYAML not available. Install with `pip install pyyaml` (or `uv add pyyaml`) "
        "to load program scopes. Minimal fallback not implemented."
    )


@lru_cache(maxsize=1)
def load_all_scopes() -> dict[str, dict[str, Any]]:
    """Load every programs/<slug>/scope.yaml. Cached per-process."""
    scopes: dict[str, dict[str, Any]] = {}
    if not PROGRAMS_DIR.exists():
        return scopes
    for prog_dir in PROGRAMS_DIR.iterdir():
        if not prog_dir.is_dir():
            continue
        scope_path = prog_dir / "scope.yaml"
        if not scope_path.exists():
            continue
        try:
            scopes[prog_dir.name] = _yaml_load(scope_path)
        except Exception:
            # Don't crash hooks on malformed scope.yaml; skip silently
            # (validation should be done by load_program.py at write time)
            continue
    return scopes


def invalidate_scope_cache() -> None:
    """For tests that mutate programs/ at runtime."""
    load_all_scopes.cache_clear()


def _entry_matches(entry: dict[str, Any], asset_type: str, identifier: str) -> bool:
    if entry.get("asset_type") != asset_type:
        return False
    entry_id = entry.get("identifier", "")
    if asset_type == "host":
        return entry_id == identifier
    if asset_type == "url":
        return identifier.startswith(entry_id) or entry_id == identifier
    if asset_type in ("package", "repo", "binary"):
        # Package: identifier may be `pkg@1.2.3` while scope entry is just `pkg`
        if "@" in identifier and "@" not in entry_id:
            base, _ = identifier.rsplit("@", 1)
            return base == entry_id
        return entry_id == identifier
    if asset_type == "ip-range":
        # CIDR matching would go here; punt for Stage 1
        return entry_id == identifier
    return entry_id == identifier


def is_in_scope(asset_type: str, identifier: str) -> tuple[bool, str | None]:
    """Check whether (asset_type, identifier) is in any loaded scope.

    Returns (in_scope, program_slug | None).
    Out-of-scope explicit matches return (False, None) regardless of in_scope match.
    """
    scopes = load_all_scopes()
    matched_program = None

    # First, check explicit out-of-scope across ALL programs (out-of-scope wins)
    for slug, scope in scopes.items():
        for entry in scope.get("out_of_scope", []) or []:
            if _entry_matches(entry, asset_type, identifier):
                return False, None

    # Then, check in-scope
    for slug, scope in scopes.items():
        for entry in scope.get("in_scope", []) or []:
            if _entry_matches(entry, asset_type, identifier):
                matched_program = slug
                break
        if matched_program:
            break

    return (matched_program is not None), matched_program


def host_in_scope(host_or_url: str) -> tuple[bool, str | None]:
    """Convenience: extract host from URL (or use as-is) and check scope."""
    if "://" in host_or_url:
        parsed = urlparse(host_or_url)
        host = parsed.hostname or ""
    else:
        host = host_or_url
    return is_in_scope("host", host)


# Pattern: extract package@version mentions from text
PACKAGE_MENTION_RE = re.compile(r"\b([a-zA-Z0-9][a-zA-Z0-9._-]+)@(\d+\.[\w.+-]+)\b")
# Pattern: extract URLs / hostnames from text
URL_RE = re.compile(r"https?://([a-zA-Z0-9.-]+)(/[^\s\"<>]*)?", re.IGNORECASE)
# Pattern: extract GitHub repo references like github.com/owner/repo
GH_REPO_RE = re.compile(r"\bgithub\.com/([\w.-]+)/([\w.-]+)", re.IGNORECASE)


def extract_targets_from_text(text: str) -> list[tuple[str, str]]:
    """Pull (asset_type, identifier) candidates from arbitrary text. Used by UPS-2."""
    targets: list[tuple[str, str]] = []
    for m in PACKAGE_MENTION_RE.finditer(text):
        targets.append(("package", m.group(0)))
    for m in URL_RE.finditer(text):
        host = m.group(1)
        targets.append(("host", host))
        targets.append(("url", m.group(0)))
    for m in GH_REPO_RE.finditer(text):
        targets.append(("repo", f"github.com/{m.group(1)}/{m.group(2)}"))
    return targets
