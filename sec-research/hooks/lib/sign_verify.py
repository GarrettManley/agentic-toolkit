"""HMAC-SHA256 sign/verify for override + approval tokens.

The HMAC key lives at ~/.claude/sec-research-override-key (outside the repo).
If the key file is missing, signing AND verifying both fail — by design.
This means override tokens cannot be created or honored without the human-controlled key.

Canonical JSON: keys sorted, separators=(',',':'), no whitespace.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import OVERRIDE_KEY_PATH


def _load_key() -> bytes:
    if not OVERRIDE_KEY_PATH.exists():
        raise FileNotFoundError(
            f"Override HMAC key not found at {OVERRIDE_KEY_PATH}. "
            f"Generate via: python -c \"import secrets; print(secrets.token_hex(32))\" > {OVERRIDE_KEY_PATH}"
        )
    raw = OVERRIDE_KEY_PATH.read_text(encoding="utf-8").strip()
    if len(raw) < 32:
        raise ValueError(f"Key at {OVERRIDE_KEY_PATH} is too short ({len(raw)} chars)")
    return raw.encode("utf-8")


def canonical_json(obj: dict[str, Any]) -> bytes:
    """Stable, deterministic JSON encoding for signing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign_token(payload: dict[str, Any]) -> str:
    """Sign a token payload (dict without 'signature' key). Returns hex digest."""
    if "signature" in payload:
        raise ValueError("payload must not contain 'signature'; sign produces it")
    key = _load_key()
    return hmac.new(key, canonical_json(payload), hashlib.sha256).hexdigest()


def verify_token(token: dict[str, Any]) -> tuple[bool, str | None]:
    """Verify a token's signature. Returns (ok, error_message)."""
    if "signature" not in token:
        return False, "token missing 'signature' field"
    sig = token["signature"]
    payload = {k: v for k, v in token.items() if k != "signature"}
    try:
        expected = sign_token(payload)
    except FileNotFoundError as exc:
        return False, str(exc)
    if not hmac.compare_digest(sig, expected):
        return False, "signature mismatch (forged or wrong key)"
    return True, None


def is_expired(token: dict[str, Any], now: datetime | None = None) -> bool:
    """Check if token is past its expires_at."""
    now = now or datetime.now(timezone.utc)
    expires_at_str = token.get("expires_at")
    if not expires_at_str:
        return True
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
    except ValueError:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now >= expires_at


def is_within_ceilings(token: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate hard ceilings: max_uses <= 5, expires_at <= created_at + 24h."""
    max_uses = token.get("max_uses", 1)
    if max_uses < 1 or max_uses > 5:
        return False, f"max_uses {max_uses} out of [1,5]"
    try:
        created = datetime.fromisoformat(token["created_at"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        return False, f"missing or malformed timestamp: {exc}"
    delta = expires - created
    if delta.total_seconds() < 0:
        return False, "expires_at before created_at"
    if delta.total_seconds() > 24 * 3600:
        return False, "expires_at more than 24h after created_at (hard ceiling)"
    return True, None
