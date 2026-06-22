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
    cleaned = re.sub(r"\.git$", "", raw.rstrip("/"))
    m = re.search(r"github\.com[/:]([^/\s]+)/([^/\s]+)", cleaned)
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
