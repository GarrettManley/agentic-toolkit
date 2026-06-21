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
