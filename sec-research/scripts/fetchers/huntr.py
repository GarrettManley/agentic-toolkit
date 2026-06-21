"""huntr.com program scope fetcher.

huntr exposes no public scope API, so we scrape the public program page
https://huntr.com/repos/<owner>/<pkg> and read its embedded __NEXT_DATA__ JSON.
Tests feed canned page bodies via from_fixture; production fetches live (gated by
_http). Ecosystem is read from the page when present, else inferred by probing the
linked GitHub repo manifest. The capture date is recorded in rules.notes.

⚠️  RECONCILE NOTE: The __NEXT_DATA__ key path
    props → pageProps → repo → {owner, name, ecosystem, repository_url, display_name}
    is the *assumed* Next.js shape inferred from the brief. Verify against a real
    huntr page capture before enabling live production use. Fixture tests assert
    the mapping logic, not real-world page fidelity.
"""
from __future__ import annotations

import json
import re

from fetchers import _http
from fetchers._common import (
    FetchResult,
    infer_ecosystem_from_manifest,
    slugify,
    utc_now_iso,
)

_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


def _parse_repo(html: str) -> dict | None:
    """Return the repo object from the embedded JSON, or None if unparseable.

    RECONCILE these keys with a real huntr capture before trusting in production.
    """
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
    """Fetch and normalize a huntr program scope for the given identifier.

    Args:
        identifier: "<owner>/<pkg>" as it appears in the huntr URL path.
        from_fixture: Path to a canned HTML file; skips the live HTTP call.
        manifest_fixture: Path to a canned GitHub contents JSON file; skips
            the live gh-api manifest probe when ecosystem is absent from the page.

    Returns:
        FetchResult with ok=True and schema-valid data on success; ok=False
        with a parse warning on a bad/garbage page; ok=False with an identifier
        warning when no "/" is present in the identifier. Never raises.
    """
    if "/" not in identifier:
        return FetchResult(
            ok=False,
            slug="",
            data=None,
            warnings=[f"identifier must be '<owner>/<pkg>', got {identifier!r}"],
        )

    owner, pkg = identifier.split("/", 1)
    url = f"https://huntr.com/repos/{owner}/{pkg}"
    slug = f"huntr-{slugify(identifier)}"

    try:
        html = _http.http_get(url, from_fixture=from_fixture)
    except _http.HttpError as e:
        return FetchResult(ok=False, slug=slug, data=None, warnings=[str(e)])

    repo = _parse_repo(html)
    if repo is None:
        return FetchResult(
            ok=False,
            slug=slug,
            data=None,
            warnings=["could not parse huntr page shape (no __NEXT_DATA__ repo blob)"],
        )

    warnings: list[str] = []
    ecosystem = repo.get("ecosystem") or None  # treat empty string as absent

    # Probe the manifest only when the page is silent AND we are allowed to do live
    # work (fixture mode does no network unless an explicit manifest_fixture is supplied).
    if not ecosystem and (manifest_fixture is not None or from_fixture is None):
        ecosystem, eco_warn = infer_ecosystem_from_manifest(
            owner, pkg, contents_fixture=manifest_fixture
        )
        warnings += eco_warn
    elif not ecosystem:
        warnings.append(
            "ecosystem not on page and probe skipped (fixture mode); ecosystem omitted"
        )

    pkg_entry: dict = {"asset_type": "package", "identifier": pkg}
    if ecosystem:
        pkg_entry["ecosystem"] = ecosystem
    pkg_entry["notes"] = "Package under huntr program scope"

    repo_entry: dict = {
        "asset_type": "repo",
        "identifier": f"github.com/{owner}/{pkg}",
        "notes": "Source repo for the package",
    }

    now = utc_now_iso()
    scope: dict = {
        "program_slug": slug,
        "venue": "huntr",
        "venue_program_id": identifier,
        "loaded_at": now,
        "loaded_from": url,
        "display_name": repo.get("display_name") or f"{owner} — {pkg}",
        "in_scope": [pkg_entry, repo_entry],
        "out_of_scope": [],
        "rules": {
            "ai_assistance_allowed": True,
            "ai_disclosure_required": True,
            "rate_limit_per_min": 60,
            "user_agent_required": "Garrett-Manley-SecResearch/1.0 (huntr.com/research)",
            "no_dast_against_prod": True,
            "notes": f"Captured from {url} on {now}.",
        },
        "submission": {
            "protocol": "manual-form",
            "endpoint": url,
        },
    }
    return FetchResult(ok=True, slug=slug, data=scope, warnings=warnings)
