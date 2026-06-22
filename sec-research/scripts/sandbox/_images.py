"""Per-ecosystem sandbox image, registry host, and safe-install env.

REGISTRY_HOSTS is the install-phase allow-set passed to policy.check_http.
safe_install_env returns docker `-e` flag pairs that neutralize install-time
script execution where the ecosystem supports a global switch (npm). Others rely
on host-isolation in v1 (a proxy-allowlist + per-ecosystem hardening is a follow-up)."""
from __future__ import annotations


class UnknownEcosystem(ValueError):
    """Ecosystem has no configured sandbox image."""


ECOSYSTEMS: dict[str, dict] = {
    "npm": {"image": "node:22-slim", "registry": "registry.npmjs.org",
            "install_env": {"npm_config_ignore_scripts": "true"}},
    "pypi": {"image": "python:3.12-slim", "registry": "pypi.org", "install_env": {}},
    "cargo": {"image": "rust:1-slim", "registry": "crates.io", "install_env": {}},
    "rubygems": {"image": "ruby:3.3-slim", "registry": "rubygems.org", "install_env": {}},
}

REGISTRY_HOSTS: frozenset[str] = frozenset(v["registry"] for v in ECOSYSTEMS.values())


def _entry(ecosystem: str) -> dict:
    try:
        return ECOSYSTEMS[ecosystem]
    except KeyError:
        raise UnknownEcosystem(f"no sandbox image for ecosystem {ecosystem!r}")


def image_for(ecosystem: str) -> str:
    return _entry(ecosystem)["image"]


def registry_for(ecosystem: str) -> str:
    return _entry(ecosystem)["registry"]


def safe_install_env(ecosystem: str) -> list[str]:
    """Flat list of docker -e flag pairs, e.g. ['-e', 'npm_config_ignore_scripts=true']."""
    out: list[str] = []
    for k, v in _entry(ecosystem)["install_env"].items():
        out += ["-e", f"{k}={v}"]
    return out
