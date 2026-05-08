"""CVE ID validation against the NVD database, with local file cache.

Cache: runtime/cache/nvd/<cve_id>.json (24h TTL).
Lookup: NVD JSON API v2.0. Falls back to negative-cache if API unreachable.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import RUNTIME_CACHE_NVD_DIR

CVE_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,}\b")
NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CACHE_TTL_SECONDS = 24 * 3600


def extract_cve_ids(text: str) -> list[str]:
    return list(set(CVE_PATTERN.findall(text)))


def _cache_path(cve_id: str) -> Path:
    return RUNTIME_CACHE_NVD_DIR / f"{cve_id}.json"


def _load_cache(cve_id: str) -> dict[str, Any] | None:
    p = _cache_path(cve_id)
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


def _save_cache(cve_id: str, data: dict[str, Any]) -> None:
    RUNTIME_CACHE_NVD_DIR.mkdir(parents=True, exist_ok=True)
    data = {**data, "_cached_at": time.time()}
    try:
        with _cache_path(cve_id).open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass  # Cache write failures are non-fatal


def _query_nvd(cve_id: str, timeout: float = 5.0) -> dict[str, Any] | None:
    """Query NVD API. Returns the response dict or None on any failure."""
    try:
        import urllib.request
        import urllib.parse
        url = f"{NVD_API}?cveId={urllib.parse.quote(cve_id)}"
        req = urllib.request.Request(url, headers={"User-Agent": "sec-research/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def cve_exists(cve_id: str) -> tuple[bool, str | None]:
    """Check if a CVE-ID exists in NVD. Returns (exists, info_or_error).

    Special placeholders that are always allowed:
    - 'CVE-PROPOSED' (in-flight, not yet assigned)
    - 'CVE-RESERVED' (reserved but not yet published)
    """
    if cve_id in ("CVE-PROPOSED", "CVE-RESERVED"):
        return True, "placeholder (not yet assigned)"

    if not CVE_PATTERN.fullmatch(cve_id):
        return False, f"malformed CVE ID format: {cve_id}"

    cached = _load_cache(cve_id)
    if cached is not None:
        return cached.get("exists", False), cached.get("reason")

    nvd_resp = _query_nvd(cve_id)
    if nvd_resp is None:
        # Network failure: don't fail-closed in the cache; record uncertainty
        # but DO fail-closed at the call site (PT-4) — the absence of confirmation
        # is itself a reason to block.
        _save_cache(cve_id, {"exists": False, "reason": "NVD unreachable; could not confirm"})
        return False, "NVD unreachable; could not confirm CVE existence"

    vulns = nvd_resp.get("vulnerabilities", [])
    if not vulns:
        _save_cache(cve_id, {"exists": False, "reason": "not found in NVD"})
        return False, "CVE not found in NVD"

    _save_cache(cve_id, {"exists": True, "reason": None})
    return True, None


def validate_cve_ids_in_text(text: str) -> list[tuple[str, str]]:
    """Find all CVE IDs in text and return list of (cve_id, error) for failures.

    Returns empty list if all CVEs are valid.
    """
    failures: list[tuple[str, str]] = []
    for cve_id in extract_cve_ids(text):
        ok, err = cve_exists(cve_id)
        if not ok:
            failures.append((cve_id, err or "unknown error"))
    return failures
