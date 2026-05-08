"""Test that override tokens are single-use by default and forgery is detected."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _sign_test_token(workspace_root: Path, rule: str, target: str, max_uses: int = 1) -> str:
    """Helper: sign a token by invoking sign_override.py with --test-mode-confirm."""
    cmd = [
        sys.executable,
        str(workspace_root / "scripts" / "sign_override.py"),
        "--rule", rule,
        "--target", target,
        "--reason", "test override for unit test verification of behavior",
        "--max-uses", str(max_uses),
        "--ttl-hours", "1",
        "--test-mode-confirm",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace_root))
    assert result.returncode == 0, f"sign_override failed: {result.stderr}"
    # Extract token id from stdout
    for line in result.stdout.splitlines():
        if "Token signed and written" in line:
            return Path(line.split(": ", 1)[1]).stem
    raise RuntimeError(f"could not find token id in: {result.stdout}")


def test_sign_override_creates_signed_token(override_key_setup, clean_overrides, workspace_root):
    token_id = _sign_test_token(workspace_root, "PT-1", "test.example.com")
    token_path = workspace_root / "overrides" / "signed" / f"{token_id}.json"
    assert token_path.exists()
    with token_path.open("r", encoding="utf-8") as f:
        token = json.load(f)
    assert token["rule_id"] == "PT-1"
    assert token["scope"]["target"] == "test.example.com"
    assert "signature" in token
    assert len(token["signature"]) == 64  # HMAC-SHA256 hex


def test_forged_token_signature_rejected(override_key_setup, clean_overrides, workspace_root):
    token_id = _sign_test_token(workspace_root, "PT-1", "test.example.com")
    token_path = workspace_root / "overrides" / "signed" / f"{token_id}.json"

    # Tamper: change target after signing
    with token_path.open("r", encoding="utf-8") as f:
        token = json.load(f)
    token["scope"]["target"] = "evil.example.com"
    with token_path.open("w", encoding="utf-8") as f:
        json.dump(token, f)

    # Verify
    from lib.sign_verify import verify_token
    ok, err = verify_token(token)
    assert not ok
    assert "signature mismatch" in (err or "")


def test_expired_token_rejected(override_key_setup, clean_overrides, workspace_root):
    """Token past its expires_at should be considered expired regardless of signature."""
    from lib.sign_verify import is_expired
    expired_token = {
        "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    assert is_expired(expired_token)


def test_max_uses_ceiling_enforced(override_key_setup, clean_overrides, workspace_root):
    """sign_override should reject max_uses > 5."""
    cmd = [
        sys.executable,
        str(workspace_root / "scripts" / "sign_override.py"),
        "--rule", "PT-1",
        "--target", "test.example.com",
        "--reason", "test override for ceiling validation behavior",
        "--max-uses", "6",
        "--test-mode-confirm",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace_root))
    assert result.returncode != 0
    assert "max_uses" in result.stderr or "max_uses" in result.stdout


def test_ttl_ceiling_enforced(override_key_setup, clean_overrides, workspace_root):
    """sign_override should reject ttl-hours > 24."""
    cmd = [
        sys.executable,
        str(workspace_root / "scripts" / "sign_override.py"),
        "--rule", "PT-1",
        "--target", "test.example.com",
        "--reason", "test override for TTL validation behavior",
        "--ttl-hours", "25",
        "--test-mode-confirm",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace_root))
    assert result.returncode != 0
    assert "ttl-hours" in result.stderr or "ttl-hours" in result.stdout
