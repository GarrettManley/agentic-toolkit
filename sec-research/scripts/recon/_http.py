"""HTTP egress chokepoint for recon. Every live call is gated by policy.check_http
against RECON_INFRA_HOSTS BEFORE the socket opens. from_fixture returns canned
bodies and opens no socket (gate skipped). ScopeViolation propagates uncaught."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from lib.policy import check_http
from recon._hosts import RECON_INFRA_HOSTS

USER_AGENT = "Garrett-Manley-SecResearch/1.0 (recon)"


class HttpError(RuntimeError):
    """A live HTTP call failed (network/timeout/HTTP-error)."""


def gate(url: str) -> None:
    """Raise ScopeViolation if url's host is not in scope or RECON_INFRA_HOSTS."""
    check_http(url, bootstrap_hosts=RECON_INFRA_HOSTS)


def http_get(url: str, *, headers: dict | None = None, from_fixture=None,
             timeout: float = 15.0) -> str:
    if from_fixture is not None:
        return Path(from_fixture).read_text(encoding="utf-8")
    gate(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise HttpError(f"GET {url} -> HTTP {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise HttpError(f"GET {url} failed: {e}") from e


def http_post_json(url: str, payload: dict, *, from_fixture=None,
                   timeout: float = 30.0) -> dict:
    if from_fixture is not None:
        return json.loads(Path(from_fixture).read_text(encoding="utf-8"))
    gate(url)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HttpError(f"POST {url} -> HTTP {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise HttpError(f"POST {url} failed: {e}") from e
