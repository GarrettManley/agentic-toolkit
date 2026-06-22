"""HTTP egress chokepoint for the collector.

Every real network read goes through `fetch_url`. `from_fixture=` returns a canned
body and opens no socket, so tests never touch the network (the fixture seam,
cloned from sec-research/scripts/fetchers/_http.py)."""

from __future__ import annotations

from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "hw-dashboard-collector/0.1 (+local price tracker)"
)


class FetchError(RuntimeError):
    """A live HTTP GET failed (network/timeout/HTTP-error)."""


def fetch_url(
    url: str,
    *,
    from_fixture: str | Path | None = None,
    headers: dict | None = None,
    timeout: float = 10.0,
) -> str:
    if from_fixture is not None:
        return Path(from_fixture).read_text(encoding="utf-8")
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
                **(headers or {}),
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        raise FetchError(f"GET {url} failed: {e}") from e
