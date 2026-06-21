"""IBB-on-HackerOne scope fetcher. IBB is one H1 program covering many OSS packages;
we fetch one program/asset per invocation. Reads are reputation-gated — on 401/403 or
a missing credential we emit a draft scaffold for manual completion rather than failing
hard. submission.protocol is manual-form for Stage 2 (h1-api arrives in Stage 7).

⚠️  RECONCILE NOTE: The H1 structured_scopes JSON shape
    meta.{program_handle, embargo_period_days, ai_assistance_allowed, ai_disclosure_required}
    data[].attributes.{asset_identifier, asset_type, eligible_for_bounty, eligible_for_submission}
    is a documented *assumption* inferred from the H1 API docs. Reconcile it with a real
    api.hackerone.com response (requires an H1 token) before production use.
"""
from __future__ import annotations

import json
from pathlib import Path

from fetchers import _http
from fetchers._common import FetchResult, slugify, utc_now_iso
from lib.credentials import get_credential

H1_API = "https://api.hackerone.com/v1"
DEFAULT_H1_USER = "garrettmanley"


def _is_denied(payload: dict) -> bool:
    """Return True if the payload signals an auth/reputation denial (HTTP 401/403)."""
    for err in payload.get("errors", []) or []:
        if str(err.get("status")) in {"401", "403"}:
            return True
    return False


def _scaffold_draft(identifier: str, slug: str, reason: str) -> FetchResult:
    """Return a schema-valid draft skeleton with explanatory warnings.

    The skeleton has a single placeholder in_scope entry so that the
    program.schema.json minItems: 1 constraint is satisfied. The draft flag
    routes the CLI to scope.draft.yaml rather than scope.yaml for manual review.
    """
    skeleton = {
        "program_slug": slug,
        "venue": "ibb-h1",
        "venue_program_id": identifier,
        "loaded_at": utc_now_iso(),
        "loaded_from": "https://hackerone.com/ibb",
        "display_name": f"IBB — {identifier} (DRAFT)",
        "in_scope": [
            {
                "asset_type": "package",
                "identifier": identifier,
                "notes": "PLACEHOLDER — confirm asset against H1 program scope before use",
            }
        ],
        "out_of_scope": [],
        "rules": {
            "ai_assistance_allowed": True,
            "ai_disclosure_required": True,
            "embargo_period_days": 90,
            "notes": (
                f"DRAFT scaffold ({reason}); complete manually then load via load_program.py."
            ),
        },
        "submission": {
            "protocol": "manual-form",
            "endpoint": "https://hackerone.com/ibb",
        },
    }
    return FetchResult(
        ok=True,
        slug=slug,
        data=skeleton,
        draft=True,
        warnings=[
            f"IBB read denied ({reason}); emitted scope.draft.yaml for manual completion"
        ],
    )


def _build_from_payload(identifier: str, slug: str, payload: dict) -> FetchResult:
    """Map a parsed H1 structured_scopes payload to a FetchResult.

    VDP-only assets (eligible_for_submission but not eligible_for_bounty) are
    routed to out_of_scope with an explicit reason rather than silently included.
    If no bounty-eligible assets exist, falls back to a draft scaffold.
    """
    if _is_denied(payload):
        return _scaffold_draft(identifier, slug, "reputation-gated (HTTP 401/403)")

    meta = payload.get("meta", {})
    in_scope: list[dict] = []
    out_of_scope: list[dict] = []

    for asset in payload.get("data", []):
        attr = asset.get("attributes", {})
        aid = attr.get("asset_identifier")
        if not aid:
            continue
        if attr.get("eligible_for_bounty"):
            in_scope.append(
                {
                    "asset_type": "package",
                    "identifier": aid,
                    "notes": "IBB bounty-eligible asset",
                }
            )
        elif attr.get("eligible_for_submission"):
            out_of_scope.append(
                {
                    "asset_type": "package",
                    "identifier": aid,
                    "reason": "VDP-only, not bounty-eligible",
                }
            )

    if not in_scope:
        return _scaffold_draft(identifier, slug, "no bounty-eligible asset found in payload")

    now = utc_now_iso()
    program_handle = meta.get("program_handle", identifier)
    scope: dict = {
        "program_slug": slug,
        "venue": "ibb-h1",
        "venue_program_id": program_handle,
        "loaded_at": now,
        "loaded_from": f"https://hackerone.com/{program_handle}",
        "display_name": f"IBB — {identifier}",
        "in_scope": in_scope,
        "out_of_scope": out_of_scope,
        "rules": {
            "ai_assistance_allowed": bool(meta.get("ai_assistance_allowed", True)),
            "ai_disclosure_required": bool(meta.get("ai_disclosure_required", True)),
            "rate_limit_per_min": 60,
            "embargo_period_days": int(meta.get("embargo_period_days", 90)),
            "notes": f"Captured from H1 structured_scopes on {now}.",
        },
        "submission": {
            "protocol": "manual-form",
            "endpoint": f"https://hackerone.com/{program_handle}",
        },
    }
    return FetchResult(ok=True, slug=slug, data=scope)


def fetch(identifier: str, *, from_fixture=None, username=None) -> FetchResult:
    """Fetch and normalize an IBB program scope for the given asset identifier.

    Args:
        identifier: The OSS package/asset name as used in the H1 IBB program
                    (e.g. "django", "flask").
        from_fixture: Path to a canned JSON file (H1 structured_scopes shape);
                      skips the live network call. Used by tests.
        username:    H1 API username for Basic auth. Defaults to DEFAULT_H1_USER.

    Returns:
        FetchResult with ok=True and schema-valid data on success.
        FetchResult with ok=True, draft=True and a scaffold skeleton on 401/403,
        missing credential, or a payload with no bounty-eligible assets.
        FetchResult with ok=False only on unexpected HTTP errors.
    """
    slug = f"ibb-{slugify(identifier)}"

    if from_fixture is not None:
        payload = json.loads(Path(from_fixture).read_text(encoding="utf-8"))
        return _build_from_payload(identifier, slug, payload)

    # Live path: resolve H1 credential via keyring then fetch structured scopes.
    h1_user = username or DEFAULT_H1_USER
    token = get_credential({"service": "hackerone-api", "username": h1_user})
    if not token:
        return _scaffold_draft(identifier, slug, "no hackerone-api credential configured")

    import base64
    auth = base64.b64encode(f"{h1_user}:{token}".encode()).decode()
    url = f"{H1_API}/programs/{identifier}/structured_scopes"
    try:
        body = _http.http_get(
            url,
            headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
        )
    except _http.HttpError as e:
        msg = str(e)
        if "403" in msg or "401" in msg:
            return _scaffold_draft(identifier, slug, "reputation-gated (HTTP 401/403)")
        return FetchResult(ok=False, slug=slug, data=None, warnings=[msg])
    return _build_from_payload(identifier, slug, json.loads(body))
