"""Test HMAC sign/verify primitives."""
from __future__ import annotations

import json

import pytest


def test_sign_then_verify_round_trip(override_key_setup):
    from lib.sign_verify import sign_token, verify_token

    payload = {
        "token_id": "ovr-test-001",
        "rule_id": "PT-1",
        "scope": {"target": "example.com", "reason": "test"},
        "created_at": "2026-05-07T00:00:00Z",
        "expires_at": "2026-05-07T04:00:00Z",
        "max_uses": 1,
        "created_by": "test",
    }
    sig = sign_token(payload)
    token = {**payload, "signature": sig}
    ok, err = verify_token(token)
    assert ok, f"verify failed: {err}"


def test_forged_token_fails_verify(override_key_setup):
    from lib.sign_verify import sign_token, verify_token

    payload = {
        "token_id": "ovr-test-002",
        "rule_id": "PT-1",
        "scope": {"target": "example.com", "reason": "test"},
        "created_at": "2026-05-07T00:00:00Z",
        "expires_at": "2026-05-07T04:00:00Z",
        "max_uses": 1,
        "created_by": "test",
    }
    sig = sign_token(payload)
    # Tamper with target after signing
    forged = {**payload, "signature": sig}
    forged["scope"]["target"] = "evil.com"
    ok, err = verify_token(forged)
    assert not ok
    assert "signature mismatch" in (err or "")


def test_expiry_check(override_key_setup):
    from lib.sign_verify import is_expired
    from datetime import datetime, timezone, timedelta

    fresh = {"expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    expired = {"expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}

    assert not is_expired(fresh)
    assert is_expired(expired)


def test_ceiling_24h_max(override_key_setup):
    from lib.sign_verify import is_within_ceilings

    too_long = {
        "created_at": "2026-05-07T00:00:00Z",
        "expires_at": "2026-05-08T01:00:00Z",  # 25h after
        "max_uses": 1,
    }
    ok, err = is_within_ceilings(too_long)
    assert not ok
    assert "24h" in (err or "")


def test_ceiling_max_uses_limit(override_key_setup):
    from lib.sign_verify import is_within_ceilings

    too_many = {
        "created_at": "2026-05-07T00:00:00Z",
        "expires_at": "2026-05-07T04:00:00Z",
        "max_uses": 6,
    }
    ok, err = is_within_ceilings(too_many)
    assert not ok
    assert "max_uses" in (err or "")
