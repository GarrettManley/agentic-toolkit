"""Recon data-source hosts, treated as trust-establishing infrastructure (same
category as policy.VENUE_BOOTSTRAP_HOSTS) and allowed once any scope is loaded.
Passed to policy.check_http via bootstrap_hosts; Stage-1 policy.py is not edited."""
from __future__ import annotations

RECON_INFRA_HOSTS: frozenset[str] = frozenset({
    # package registries
    "registry.npmjs.org", "pypi.org", "crates.io", "rubygems.org",
    # github (metadata, raw manifests, clone)
    "api.github.com", "raw.githubusercontent.com", "github.com",
    # advisory databases
    "services.nvd.nist.gov", "api.osv.dev",
})
