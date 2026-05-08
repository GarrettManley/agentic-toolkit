"""Subprocess-level HTTP scope check (closes the PT-1 hook gap for sanctioned scripts).

Claude's PreToolUse hooks (PT-1) intercept ``Bash``, ``WebFetch``, ``WebSearch``
and MCP-browser tool invocations. They cannot intercept HTTP calls made from
inside a script invoked via ``python scripts/foo.py`` (urllib / httpx / requests
/ subprocess.run all bypass the hook layer).

This module's :func:`check_http` is the per-call gate sanctioned subprocess
scripts (``fetch_program.py``, ``nightly.py``, ``investigate.py``) must invoke
before each HTTP request. It mirrors PT-1's authorization logic:

  1. Allow if the host matches ``bootstrap_hosts`` (exact or dot-suffix).
  2. Allow if :func:`lib.scope_match.host_in_scope` returns True.
  3. Allow if a signed PT-1 override matches the host (token is consumed).
  4. Otherwise: append a ``policy-blocked`` event to the ledger and raise
     :class:`ScopeViolation`.

Threat model: honest mistakes (a script forgets to invoke ``check_http``), not
malicious bypass. Code review is the actual enforcement; the ledger entries
are the audit trail when a caller forgets.
"""
from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from .scope_match import host_in_scope
from . import ledger
# common.py is one level up from this lib/ package. All sanctioned callers
# (hooks, scripts/*.py via sys.path patching, tests/conftest.py) make hooks/
# importable, so this works in every legitimate context.
from common import find_active_override  # type: ignore[import-not-found]


VENUE_BOOTSTRAP_HOSTS: frozenset[str] = frozenset({
    "api.huntr.com", "huntr.com",
    "api.github.com",
    "api.hackerone.com", "hackerone.com",
    "api.bugcrowd.com", "bugcrowd.com",
    "api.intigriti.com", "intigriti.com",
})


class ScopeViolation(Exception):
    """Raised when a subprocess HTTP call targets a host outside policy."""

    def __init__(self, url: str, host: str, reason: str, rule_id: str = "PT-1") -> None:
        super().__init__(f"{rule_id}: {host} blocked - {reason} (url={url})")
        self.url = url
        self.host = host
        self.reason = reason
        self.rule_id = rule_id


def _extract_host(url: str) -> str:
    """Extract hostname from a URL or bare host string."""
    if "://" in url:
        return urlparse(url).hostname or ""
    return url.split("/", 1)[0]


def _matches_bootstrap(host: str, bootstrap_hosts: Iterable[str]) -> bool:
    """Match host against bootstrap_hosts: exact or dot-suffix.

    ``api.huntr.com`` matches an entry of ``huntr.com``; ``huntr.com.evil`` does not.
    """
    for entry in bootstrap_hosts:
        if host == entry or host.endswith("." + entry):
            return True
    return False


def check_http(
    url: str,
    *,
    bootstrap_hosts: Iterable[str] = (),
    rule_id: str = "PT-1",
) -> tuple[bool, str | None]:
    """Authorize a subprocess HTTP call.

    Returns ``(True, slug_or_None)`` on allow; raises :class:`ScopeViolation` on
    block. A ``policy-blocked`` event is appended to the ledger before raising
    (best-effort; ledger failure does NOT suppress the raise).

    Args:
        url: Full URL or bare host (``"github.com/owner/repo"``).
        bootstrap_hosts: Hosts allowed without a loaded program scope. Pass
            :data:`VENUE_BOOTSTRAP_HOSTS` for venue fetchers; default ``()``
            forces every call into scope-or-override.
        rule_id: Policy rule name for the ledger entry and exception (default
            ``"PT-1"``).
    """
    host = _extract_host(url)

    if _matches_bootstrap(host, bootstrap_hosts):
        return True, None

    in_scope, prog = host_in_scope(url)
    if in_scope:
        return True, prog

    if find_active_override(rule_id, host):
        return True, None

    reason = "host not in any loaded scope, not in bootstrap_hosts, no active override"
    try:
        ledger.append_event(
            "policy-blocked",
            rule_id=rule_id,
            url=url,
            host=host,
            reason=reason,
        )
    except Exception:
        # Ledger outage must NOT suppress the security-critical raise.
        pass

    raise ScopeViolation(url=url, host=host, reason=reason, rule_id=rule_id)
