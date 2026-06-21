"""HTTP egress chokepoint for venue fetchers.

Every real network call is gated by policy.check_http BEFORE the socket opens
(or before shelling out to `gh api`). --from-fixture returns canned bodies and
opens no socket, so the gate is skipped in fixture mode. ScopeViolation from the
gate propagates uncaught (it carries an audit side effect)."""
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from lib.policy import VENUE_BOOTSTRAP_HOSTS, check_http

USER_AGENT = "Garrett-Manley-SecResearch/1.0"


class HttpError(RuntimeError):
    """A live HTTP GET failed (network/timeout/HTTP-error)."""


class GhApiError(RuntimeError):
    """`gh api` exited non-zero, was not found, or returned non-JSON."""


def http_get(url: str, *, headers: dict | None = None, from_fixture=None,
             timeout: float = 10.0) -> str:
    if from_fixture is not None:
        return Path(from_fixture).read_text(encoding="utf-8")
    check_http(url, bootstrap_hosts=VENUE_BOOTSTRAP_HOSTS)  # raises ScopeViolation on block
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise HttpError(f"GET {url} -> HTTP {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise HttpError(f"GET {url} failed: {e}") from e


def gh_api_json(path: str, *, from_fixture=None, timeout: float = 30.0):
    if from_fixture is not None:
        return json.loads(Path(from_fixture).read_text(encoding="utf-8"))
    # gh hits api.github.com; gate on the synthesized URL before shelling out.
    check_http(f"https://api.github.com{path}", bootstrap_hosts=VENUE_BOOTSTRAP_HOSTS)
    try:
        proc = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise GhApiError("gh CLI not installed; install from cli.github.com")
    except subprocess.TimeoutExpired:
        raise GhApiError(f"gh api timed out after {timeout}s")
    if proc.returncode != 0:
        raise GhApiError(f"gh api failed: {proc.stderr.strip()[:500]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise GhApiError("gh api response was not JSON")
