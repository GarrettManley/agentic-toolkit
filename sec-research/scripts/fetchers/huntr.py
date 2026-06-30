"""huntr.com program scope fetcher.

huntr exposes no public scope API (api.huntr.com does not resolve), so we confirm
a program exists by fetching its public repo page https://huntr.com/repos/<owner>/
<pkg>. As of 2026-06-30 huntr runs the Next.js App Router: the page is a client-
rendered shell whose server HTML carries NO structured repo metadata (no old
Next.js data blob, no ecosystem/display_name/repository_url JSON). The shell also
returns HTTP 200 for nonexistent repos, so the status code cannot signal existence.
The reliable server-rendered signal is the <head> og:url canonical meta, which a
real repo renders to its own URL and the 404 page omits entirely. We therefore:
  - confirm existence via og:url present AND == the requested repos/<owner>/<pkg>;
  - take ecosystem from the GitHub manifest probe (the page is always silent now);
  - use the f"{owner} - {pkg}" default for display_name.
Note: the manifest probe assumes the huntr <owner>/<pkg> maps to github.com/<owner>/
<pkg> (true for the v1 npm targets; revisit for fork/rename — see hb-dzu part 2).
Tests feed canned page bodies via from_fixture; production fetches live (gated by
_http). Fixtures carry the real <head> shapes from live captures (hb-dzu).
"""
from __future__ import annotations

import re

from fetchers import _http
from fetchers._common import (
    FetchResult,
    infer_ecosystem_from_manifest,
    slugify,
    utc_now_iso,
)

# Canonical-URL meta, server-rendered in <head>; content is the exact repo URL.
# Order-robust: huntr currently emits property-before-content, but match either
# ordering so an attribute reorder upstream does not silently fail the live gate.
_OG_URL_RE = re.compile(
    r'<meta\b(?=[^>]*\bproperty=["\']og:url["\'])(?=[^>]*\bcontent=["\']([^"\']+)["\'])',
    re.IGNORECASE,
)


def _parse_og_url(html: str) -> str | None:
    """Return the <head> og:url canonical content (trailing slash stripped), or
    None if the page renders no og:url meta.

    A real repo renders og:url to its own URL; huntr's 404 page (also served with
    HTTP 200) omits og:url entirely. The caller compares the returned value to the
    requested URL — keeping the raw value here lets it distinguish "absent" (404)
    from "present but mismatched" (a real repo whose page shape drifted).
    """
    m = _OG_URL_RE.search(html)
    if not m:
        return None
    return m.group(1).strip().rstrip("/")


def fetch(identifier: str, *, from_fixture=None, manifest_fixture=None) -> FetchResult:
    """Fetch and normalize a huntr program scope for the given identifier.

    Args:
        identifier: "<owner>/<pkg>" as it appears in the huntr URL path.
        from_fixture: Path to a canned HTML file; skips the live HTTP call.
        manifest_fixture: Path to a canned GitHub contents JSON file; skips
            the live gh-api manifest probe used to infer the ecosystem.

    Returns:
        FetchResult with ok=True and schema-valid data on success; ok=False
        with a warning when the page does not confirm the repo (404/wrong shape)
        or the identifier lacks a "/". Never raises.
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

    # Confirm existence via the <head> og:url canonical meta. Distinguish "no
    # og:url" (404 / not a repo page) from "og:url present but mismatched" (a real
    # repo whose page shape drifted) — collapsing them would misreport a drifted
    # in-policy program as nonexistent and silently fail the gate it was built for.
    og_url = _parse_og_url(html)
    if og_url != url.rstrip("/"):
        if og_url is None:
            detail = "no og:url in <head> (page is a 404 or not a huntr repo page)"
        else:
            detail = (
                f"og:url present but did not match: got {og_url!r}, expected "
                f"{url.rstrip('/')!r} — possible huntr page-shape drift, not "
                "necessarily a missing repo"
            )
        return FetchResult(
            ok=False, slug=slug, data=None,
            warnings=[f"could not confirm huntr page: {detail}"],
        )

    warnings: list[str] = []
    # The App Router page carries no ecosystem; probe the manifest whenever we are
    # allowed to do live work (fixture mode probes only with an explicit manifest_fixture).
    ecosystem = None
    if manifest_fixture is not None or from_fixture is None:
        ecosystem, eco_warn = infer_ecosystem_from_manifest(
            owner, pkg, contents_fixture=manifest_fixture
        )
        warnings += eco_warn
    else:
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
        "display_name": f"{owner} — {pkg}",
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
