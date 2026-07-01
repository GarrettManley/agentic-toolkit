"""End-to-end proof that sign_override.py's --test-mode-confirm refuses to bypass the
interactive confirmation outside a pytest process (design §3)."""
from __future__ import annotations

import os
import subprocess
import sys


def _env_without_pytest_marker() -> dict:
    env = dict(os.environ)
    env.pop("PYTEST_CURRENT_TEST", None)
    return env


def test_test_mode_confirm_refused_outside_pytest(override_key_setup, clean_overrides, workspace_root):
    cmd = [
        sys.executable,
        str(workspace_root / "scripts" / "sign_override.py"),
        "--rule", "PT-1",
        "--target", "test.example.com",
        "--reason", "regression coverage for the test-mode-confirm gate itself",
        "--test-mode-confirm",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(workspace_root),
        env=_env_without_pytest_marker(), input="",
    )
    assert result.returncode == 1
    assert "only honored" in result.stderr
    signed_dir = workspace_root / "overrides" / "signed"
    assert not signed_dir.exists() or not list(signed_dir.iterdir())


def test_test_mode_confirm_still_works_under_pytest(override_key_setup, clean_overrides, workspace_root):
    """Regression: tests/hooks/test_override_singleuse.py depends on this exact CLI
    invocation succeeding via subprocess.run's default environment inheritance."""
    cmd = [
        sys.executable,
        str(workspace_root / "scripts" / "sign_override.py"),
        "--rule", "PT-1",
        "--target", "test.example.com",
        "--reason", "confirming the happy path still works under pytest",
        "--test-mode-confirm",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace_root))
    assert result.returncode == 0, f"expected success under pytest env, got: {result.stderr}"
    assert "Token signed and written" in result.stdout
