"""Per-provider egress allowlists. Passed to policy.check_http as bootstrap_hosts;
deliberately NOT added to policy.VENUE_BOOTSTRAP_HOSTS (those are venue hosts)."""
from __future__ import annotations

LLAMA_BOOTSTRAP_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1"})
CLAUDE_BOOTSTRAP_HOSTS: frozenset[str] = frozenset({"api.anthropic.com"})

BOOTSTRAP_BY_PROVIDER: dict[str, frozenset[str]] = {
    "llama": LLAMA_BOOTSTRAP_HOSTS,
    "claude": CLAUDE_BOOTSTRAP_HOSTS,
}
