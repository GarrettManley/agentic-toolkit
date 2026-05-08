"""Thin keyring wrapper for resolving program.submission.auth_ref to live credentials.

Credentials are stored in Windows Credential Manager (DPAPI-protected) via the
`keyring` library. Never logs the secret. Never writes it to disk.

Stage 1 needs zero populated credentials — `gh` (GHSA dispatch) uses gh CLI auth.
"""
from __future__ import annotations

from typing import Any


def get_credential(auth_ref: dict[str, Any]) -> str | None:
    """Resolve an auth_ref to its secret string, or None if not found.

    auth_ref shape: {service: str, username: str}
    Returns None if not configured (caller decides whether that's fatal).
    """
    if not auth_ref or "service" not in auth_ref or "username" not in auth_ref:
        return None
    try:
        import keyring
    except ImportError:
        raise RuntimeError(
            "keyring package not installed. Run: pip install keyring (or uv add keyring) "
            "to enable credential storage."
        )
    return keyring.get_password(auth_ref["service"], auth_ref["username"])


def set_credential(service: str, username: str, secret: str) -> None:
    """Store a credential. Only called from scripts/setup_credentials.py (interactive)."""
    try:
        import keyring
    except ImportError:
        raise RuntimeError("keyring package not installed.")
    keyring.set_password(service, username, secret)


def delete_credential(service: str, username: str) -> None:
    """Remove a stored credential."""
    try:
        import keyring
    except ImportError:
        raise RuntimeError("keyring package not installed.")
    try:
        keyring.delete_password(service, username)
    except keyring.errors.PasswordDeleteError:
        pass  # Not present; idempotent
