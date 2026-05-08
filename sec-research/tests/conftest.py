"""Shared pytest fixtures for sec-research tests.

- Generates an ephemeral HMAC override key per test session
- Backs up / restores the user's real override key if present
- Cleans the overrides/, submissions/tokens/, runtime/ dirs between tests
"""
from __future__ import annotations

import os
import secrets
import shutil
import sys
from pathlib import Path

import pytest

# Add hooks/ to sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "hooks"))


@pytest.fixture(scope="session")
def workspace_root() -> Path:
    return WORKSPACE_ROOT


@pytest.fixture(scope="session")
def override_key_setup(tmp_path_factory):
    """Set up an ephemeral HMAC key in a temp location and point the lib at it."""
    from lib import paths
    real_key_path = paths.OVERRIDE_KEY_PATH
    backup_path = real_key_path.with_suffix(".backup-test")

    # Backup user's real key if present
    if real_key_path.exists():
        shutil.copy(real_key_path, backup_path)

    # Write ephemeral key
    real_key_path.parent.mkdir(parents=True, exist_ok=True)
    real_key_path.write_text(secrets.token_hex(32), encoding="utf-8")

    yield real_key_path

    # Restore
    if backup_path.exists():
        shutil.move(str(backup_path), str(real_key_path))
    elif real_key_path.exists():
        real_key_path.unlink()


@pytest.fixture
def clean_overrides(workspace_root):
    """Empty overrides/signed/ and overrides/used/ between tests."""
    for sub in ("overrides/signed", "overrides/used", "submissions/tokens"):
        d = workspace_root / sub
        if d.exists():
            for p in d.iterdir():
                if p.is_file():
                    p.unlink()
    yield
