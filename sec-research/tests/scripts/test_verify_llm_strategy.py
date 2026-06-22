"""Tests for scripts/verify/llm_strategy.py — LLMPocStrategy defined seam.

TDD: these tests were written before the module existed and should be the
canonical contract for the seam's observable behaviour.
"""
from __future__ import annotations

import pytest

from verify.llm_strategy import LLMPocStrategy
from verify.strategy import PocStrategy


# ---------------------------------------------------------------------------
# isinstance check — runtime_checkable Protocol
# ---------------------------------------------------------------------------

def test_llm_poc_strategy_satisfies_protocol():
    """LLMPocStrategy() must pass isinstance(x, PocStrategy) (duck-typed at class level)."""
    strategy = LLMPocStrategy()
    assert isinstance(strategy, PocStrategy)


# ---------------------------------------------------------------------------
# supports() — always False in v1 (seam only)
# ---------------------------------------------------------------------------

def test_supports_returns_false_for_empty_hypothesis():
    """supports({}) must return False — not wired in v1."""
    strategy = LLMPocStrategy()
    assert strategy.supports({}) is False


def test_supports_returns_false_for_populated_hypothesis():
    """supports() must return False for any non-empty hypothesis dict."""
    strategy = LLMPocStrategy()
    hyp = {
        "hypothesis_id": "h-001",
        "program_slug": "test-program",
        "evidence_seed": {"package_ecosystem": "npm"},
    }
    assert strategy.supports(hyp) is False


def test_supports_returns_bool_not_falsy():
    """supports() return value must be exactly False (bool), not merely falsy."""
    strategy = LLMPocStrategy()
    result = strategy.supports({"anything": "goes"})
    assert result is False
    assert type(result) is bool


# ---------------------------------------------------------------------------
# build_plan() — raises NotImplementedError (seam only)
# ---------------------------------------------------------------------------

def test_build_plan_raises_not_implemented_for_empty_hypothesis():
    """build_plan({}) must raise NotImplementedError — not wired in v1."""
    strategy = LLMPocStrategy()
    with pytest.raises(NotImplementedError):
        strategy.build_plan({})


def test_build_plan_raises_not_implemented_for_any_hypothesis():
    """build_plan() raises NotImplementedError regardless of hypothesis content."""
    strategy = LLMPocStrategy()
    hyp = {
        "hypothesis_id": "h-002",
        "program_slug": "some-program",
        "evidence_seed": {
            "package_ecosystem": "npm",
            "package_name": "minimatch",
            "candidate_cve_id": "CVE-2022-3517",
        },
    }
    with pytest.raises(NotImplementedError):
        strategy.build_plan(hyp)


def test_build_plan_not_implemented_message_mentions_seam():
    """The NotImplementedError message should mention the seam / not-wired status."""
    strategy = LLMPocStrategy()
    with pytest.raises(NotImplementedError, match="seam"):
        strategy.build_plan({})


# ---------------------------------------------------------------------------
# Instantiation — no constructor arguments required
# ---------------------------------------------------------------------------

def test_llm_poc_strategy_instantiates_no_args():
    """LLMPocStrategy() should instantiate with zero arguments."""
    strategy = LLMPocStrategy()
    assert strategy is not None
