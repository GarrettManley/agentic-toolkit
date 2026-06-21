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
