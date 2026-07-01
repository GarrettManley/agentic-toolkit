"""Tests for the --test-mode-confirm gate shared by sign_approval.py and sign_override.py
(design §3: closes a live, unguarded PT-2/override bypass).
"""
from __future__ import annotations


def test_returns_false_without_pytest_marker(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from lib.test_mode_gate import test_mode_confirm_allowed
    assert test_mode_confirm_allowed() is False


def test_returns_true_with_pytest_marker(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/hooks/test_test_mode_gate.py::fake")
    from lib.test_mode_gate import test_mode_confirm_allowed
    assert test_mode_confirm_allowed() is True
