"""Tests for scripts/verify/strategy.py — PocPlan, SeedIncomplete, PocStrategy Protocol,
select_strategy dispatch."""
from __future__ import annotations

import os

import pytest

from verify.strategy import (
    PocPlan,
    PocStrategy,
    SeedIncomplete,
    select_strategy,
)


# ---------------------------------------------------------------------------
# PocPlan construction
# ---------------------------------------------------------------------------

def test_poc_plan_construction():
    plan = PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "minimatch@3.0.4"],
        install_hosts=["registry.npmjs.org"],
        trigger_cmd=["node", "trigger.js"],
        expected_trigger_exit=0,
        expected_trigger_sha256="deadbeef",
        files={"trigger.js": "process.stdout.write('REDOS_CONFIRMED\\n');"},
        template_id="npm__minimatch__CVE-2022-3517",
    )
    assert plan.ecosystem == "npm"
    assert plan.install_cmd == ["npm", "install", "minimatch@3.0.4"]
    assert plan.install_hosts == ["registry.npmjs.org"]
    assert plan.trigger_cmd == ["node", "trigger.js"]
    assert plan.expected_trigger_exit == 0
    assert plan.expected_trigger_sha256 == "deadbeef"
    assert "trigger.js" in plan.files
    assert plan.template_id == "npm__minimatch__CVE-2022-3517"


def test_poc_plan_is_frozen():
    plan = PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "pkg@1.0"],
        install_hosts=["registry.npmjs.org"],
        trigger_cmd=["node", "run.js"],
        expected_trigger_exit=0,
        expected_trigger_sha256="aabbcc",
        files={},
        template_id="some-template",
    )
    with pytest.raises(AttributeError):
        plan.ecosystem = "pypi"  # type: ignore[misc]


def test_poc_plan_empty_files_allowed():
    plan = PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "pkg@1.0"],
        install_hosts=[],
        trigger_cmd=["node", "index.js"],
        expected_trigger_exit=0,
        expected_trigger_sha256="ff00",
        files={},
        template_id="t1",
    )
    assert plan.files == {}


# ---------------------------------------------------------------------------
# SeedIncomplete
# ---------------------------------------------------------------------------

def test_seed_incomplete_is_value_error():
    """SeedIncomplete must be a ValueError subclass."""
    exc = SeedIncomplete(["package_name", "candidate_cve_id"])
    assert isinstance(exc, ValueError)


def test_seed_incomplete_carries_missing():
    """SeedIncomplete exposes the missing field names."""
    missing = ["package_name", "affected_versions_range"]
    exc = SeedIncomplete(missing)
    assert exc.missing == missing


def test_seed_incomplete_readable_message():
    """str(exc) includes the missing field names."""
    exc = SeedIncomplete(["package_name"])
    msg = str(exc)
    assert "package_name" in msg


def test_seed_incomplete_empty_list():
    """Allow construction with an empty missing list (edge case)."""
    exc = SeedIncomplete([])
    assert exc.missing == []


# ---------------------------------------------------------------------------
# PocStrategy Protocol — runtime_checkable
# ---------------------------------------------------------------------------

class _FullDuck:
    """Duck-type that satisfies PocStrategy Protocol."""

    def supports(self, hypothesis: dict) -> bool:
        return True

    def build_plan(self, hypothesis: dict):
        raise NotImplementedError


class _MissingBuildPlan:
    """Duck-type missing build_plan — should fail isinstance check."""

    def supports(self, hypothesis: dict) -> bool:
        return True


class _MissingSupports:
    """Duck-type missing supports — should fail isinstance check."""

    def build_plan(self, hypothesis: dict):
        raise NotImplementedError


def test_poc_strategy_protocol_duck_type_passes():
    """An object with both supports and build_plan passes isinstance(x, PocStrategy)."""
    assert isinstance(_FullDuck(), PocStrategy)


def test_poc_strategy_protocol_missing_build_plan_fails():
    """An object without build_plan fails isinstance check."""
    assert not isinstance(_MissingBuildPlan(), PocStrategy)


def test_poc_strategy_protocol_missing_supports_fails():
    """An object without supports fails isinstance check."""
    assert not isinstance(_MissingSupports(), PocStrategy)


def test_poc_strategy_protocol_plain_object_fails():
    """A plain object with no matching methods fails isinstance check."""
    assert not isinstance(object(), PocStrategy)


# ---------------------------------------------------------------------------
# select_strategy dispatch
# ---------------------------------------------------------------------------

def test_select_strategy_unknown_raises_value_error():
    """An unknown strategy name raises ValueError."""
    with pytest.raises(ValueError, match="bogus"):
        select_strategy("bogus")


def test_select_strategy_env_var_read(monkeypatch):
    """select_strategy(None) reads SECRESEARCH_POC_STRATEGY from env."""
    # Set to an unknown name so we get a ValueError with that name in the message,
    # proving the env var was read (not the default "templated").
    monkeypatch.setenv("SECRESEARCH_POC_STRATEGY", "env_bogus_strategy")
    with pytest.raises(ValueError, match="env_bogus_strategy"):
        select_strategy(None)


def test_select_strategy_env_var_default_is_templated(monkeypatch):
    """With no env var and name=None, default resolves to 'templated'.

    templated.py doesn't exist yet (Task 3), so we expect ImportError — NOT ValueError.
    ImportError proves the strategy name resolved to 'templated' and the lazy import
    was attempted.
    """
    monkeypatch.delenv("SECRESEARCH_POC_STRATEGY", raising=False)
    with pytest.raises(ImportError):
        select_strategy(None)


def test_select_strategy_explicit_templated_attempts_import(monkeypatch):
    """select_strategy('templated') attempts to import verify.templated (lazy import)."""
    with pytest.raises(ImportError):
        select_strategy("templated")


def test_select_strategy_explicit_llm_attempts_import(monkeypatch):
    """select_strategy('llm') attempts to import verify.llm_strategy (lazy import)."""
    with pytest.raises(ImportError):
        select_strategy("llm")


def test_select_strategy_name_lowercased(monkeypatch):
    """Strategy name is lowercased before dispatch — 'BOGUS' raises ValueError for bogus."""
    with pytest.raises(ValueError):
        select_strategy("BOGUS")


def test_select_strategy_unknown_clears_env(monkeypatch):
    """Explicit unknown name raises ValueError even if env var is set to something else."""
    monkeypatch.setenv("SECRESEARCH_POC_STRATEGY", "templated")
    with pytest.raises(ValueError, match="completely_unknown"):
        select_strategy("completely_unknown")
