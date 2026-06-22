"""HTTP egress chokepoint for the LLM package. Mirrors scripts/recon/_http.py:
gate via policy.check_http BEFORE the socket opens; from_fixture returns a canned
body and opens no socket. ScopeViolation propagates uncaught (ledger side-effect)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

from lib.policy import check_http


class HttpError(RuntimeError):
    """A live HTTP call to an LLM endpoint failed (network/timeout/HTTP-error)."""


def post_json(url: str, payload: dict, *, bootstrap_hosts: Iterable[str],
              headers: dict | None = None, from_fixture: str | None = None,
              timeout: float = 120.0) -> dict:
    if from_fixture is not None:
        return json.loads(Path(from_fixture).read_text(encoding="utf-8"))
    check_http(url, bootstrap_hosts=bootstrap_hosts)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HttpError(f"POST {url} -> HTTP {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise HttpError(f"POST {url} failed: {e}") from e
