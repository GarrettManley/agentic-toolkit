"""Tests for scripts/verify/templated.py — TemplatedPocStrategy + minimatch template.

TDD: these tests are written BEFORE the implementation. They should fail until
templated.py and templates/npm__minimatch__CVE-2022-3517.py are implemented.
"""
from __future__ import annotations

import hashlib

import pytest

from verify.strategy import PocPlan, SeedIncomplete


# ---------------------------------------------------------------------------
# Helpers — well-formed minimatch hypothesis fixture
# ---------------------------------------------------------------------------

def _minimatch_hypothesis(version: str = "3.0.4") -> dict:
    """Return a well-formed minimatch CVE-2022-3517 hypothesis dict."""
    return {
        "hypothesis_id": "hyp-test-001",
        "program_slug": "test-program",
        "target": {
            "identifier": f"minimatch@{version}",
            "version_or_revision": version,
        },
        "vuln_class": "dependency-cve",
        "evidence_seed": {
            "package_ecosystem": "npm",
            "package_name": "minimatch",
            "affected_versions_range": "<3.0.5",
            "candidate_cve_id": "CVE-2022-3517",
        },
    }


def _strategy():
    from verify.templated import TemplatedPocStrategy
    return TemplatedPocStrategy()


# ---------------------------------------------------------------------------
# TEMPLATE_REGISTRY contents
# ---------------------------------------------------------------------------

def test_registry_contains_minimatch_key():
    """TEMPLATE_REGISTRY must have the (npm, minimatch, CVE-2022-3517) key."""
    from verify.templated import TEMPLATE_REGISTRY
    assert ("npm", "minimatch", "CVE-2022-3517") in TEMPLATE_REGISTRY


def test_registry_value_is_callable():
    """The minimatch registry entry must be callable (a factory function)."""
    from verify.templated import TEMPLATE_REGISTRY
    factory = TEMPLATE_REGISTRY[("npm", "minimatch", "CVE-2022-3517")]
    assert callable(factory)


# ---------------------------------------------------------------------------
# TemplatedPocStrategy.supports()
# ---------------------------------------------------------------------------

def test_supports_true_for_minimatch_cve_2022_3517():
    """supports() returns True for a well-formed minimatch/CVE-2022-3517 hypothesis."""
    strategy = _strategy()
    assert strategy.supports(_minimatch_hypothesis()) is True


def test_supports_false_for_unregistered_package():
    """supports() returns False for a package not in the registry."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    hyp["evidence_seed"]["package_name"] = "lodash"
    hyp["evidence_seed"]["candidate_cve_id"] = "CVE-2021-9999"
    assert strategy.supports(hyp) is False


def test_supports_false_for_unregistered_cve():
    """supports() returns False when CVE is not registered (even if package matches)."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    hyp["evidence_seed"]["candidate_cve_id"] = "CVE-2099-0001"
    assert strategy.supports(hyp) is False


def test_supports_false_when_evidence_seed_missing():
    """supports() returns False (does NOT raise) when evidence_seed key is absent."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["evidence_seed"]
    assert strategy.supports(hyp) is False


def test_supports_false_when_evidence_seed_empty():
    """supports() returns False (does NOT raise) when evidence_seed is an empty dict."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    hyp["evidence_seed"] = {}
    assert strategy.supports(hyp) is False


def test_supports_false_when_seed_field_missing():
    """supports() returns False when individual seed fields are missing."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["evidence_seed"]["package_ecosystem"]
    assert strategy.supports(hyp) is False


def test_supports_case_sensitivity_ecosystem():
    """supports() uses the exact ecosystem string — 'NPM' is not registered."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    hyp["evidence_seed"]["package_ecosystem"] = "NPM"
    assert strategy.supports(hyp) is False


# ---------------------------------------------------------------------------
# TemplatedPocStrategy.build_plan() — happy path shape checks
# ---------------------------------------------------------------------------

def test_build_plan_returns_poc_plan():
    """build_plan() returns a PocPlan instance."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert isinstance(plan, PocPlan)


def test_build_plan_ecosystem_is_npm():
    """PocPlan.ecosystem must be 'npm'."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert plan.ecosystem == "npm"


def test_build_plan_install_cmd_pins_version():
    """install_cmd must pin the hypothesis version (3.0.4)."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert plan.install_cmd == ["npm", "install", "--no-save", "minimatch@3.0.4"]


def test_build_plan_install_cmd_pins_version_305():
    """install_cmd pins whatever version is in the hypothesis — also works for 3.0.5."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.5"))
    assert plan.install_cmd == ["npm", "install", "--no-save", "minimatch@3.0.5"]


def test_build_plan_install_hosts():
    """install_hosts must include registry.npmjs.org."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert plan.install_hosts == ["registry.npmjs.org"]


def test_build_plan_trigger_cmd():
    """trigger_cmd must be ['node', 'trigger.js']."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert plan.trigger_cmd == ["node", "trigger.js"]


def test_build_plan_expected_trigger_exit_is_zero():
    """expected_trigger_exit must be 0 (sentinel success path)."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert plan.expected_trigger_exit == 0


def test_build_plan_trigger_js_in_files():
    """files must contain 'trigger.js'."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert "trigger.js" in plan.files


def test_build_plan_trigger_js_requires_minimatch():
    """trigger.js content must require minimatch."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert 'require("minimatch")' in plan.files["trigger.js"]


def test_build_plan_trigger_js_contains_sentinel():
    """trigger.js content must contain the VULN_CONFIRMED sentinel string."""
    from verify.templates.npm__minimatch__CVE_2022_3517 import SENTINEL_CONFIRMED
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert SENTINEL_CONFIRMED in plan.files["trigger.js"]


def test_build_plan_trigger_js_contains_overlong_repeat():
    """trigger.js must contain the 70000-char OVERLONG repeat (guard-presence probe)."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert "repeat(70000)" in plan.files["trigger.js"]


def test_build_plan_files_contains_package_json():
    """files must contain a stub 'package.json' for deterministic npm install."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert "package.json" in plan.files
    import json
    pkg = json.loads(plan.files["package.json"])
    assert pkg.get("name") == "poc"
    assert pkg.get("private") is True


def test_build_plan_template_id():
    """template_id must be 'npm:minimatch:CVE-2022-3517'."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert plan.template_id == "npm:minimatch:CVE-2022-3517"


# ---------------------------------------------------------------------------
# Hash-sentinel consistency — the determinism guarantee
# ---------------------------------------------------------------------------

def test_expected_sha256_matches_sentinel_plus_newline():
    """expected_trigger_sha256 must equal sha256(SENTINEL_CONFIRMED + '\\n').

    This is the determinism invariant: the Python hash is derived from the same
    sentinel string that trigger.js writes to stdout. They can never drift.
    SENTINEL_CONFIRMED == "VULN_CONFIRMED" (guard-presence probe mechanism).
    """
    from verify.templates.npm__minimatch__CVE_2022_3517 import SENTINEL_CONFIRMED
    assert SENTINEL_CONFIRMED == "VULN_CONFIRMED", (
        f"Sentinel changed from expected 'VULN_CONFIRMED'; got {SENTINEL_CONFIRMED!r}"
    )
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    expected_hash = hashlib.sha256((SENTINEL_CONFIRMED + "\n").encode()).hexdigest()
    assert plan.expected_trigger_sha256 == expected_hash


def test_sentinel_appears_in_trigger_js():
    """The sentinel string the hash is computed from actually appears in trigger.js.

    Guards against computing the hash offline from a different string than what
    the JS script actually emits.
    """
    from verify.templates.npm__minimatch__CVE_2022_3517 import SENTINEL_CONFIRMED
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    assert SENTINEL_CONFIRMED in plan.files["trigger.js"]


def test_sha256_is_hex_string_of_correct_length():
    """expected_trigger_sha256 is a 64-char hex string (sha256 output)."""
    strategy = _strategy()
    plan = strategy.build_plan(_minimatch_hypothesis("3.0.4"))
    sha = plan.expected_trigger_sha256
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)


# ---------------------------------------------------------------------------
# build_plan() SeedIncomplete — missing / blank evidence_seed fields
# ---------------------------------------------------------------------------

def test_build_plan_raises_seed_incomplete_missing_cve():
    """SeedIncomplete raised when candidate_cve_id is missing."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["evidence_seed"]["candidate_cve_id"]
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "candidate_cve_id" in exc.value.missing


def test_build_plan_raises_seed_incomplete_missing_ecosystem():
    """SeedIncomplete raised when package_ecosystem is missing."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["evidence_seed"]["package_ecosystem"]
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "package_ecosystem" in exc.value.missing


def test_build_plan_raises_seed_incomplete_missing_package_name():
    """SeedIncomplete raised when package_name is missing."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["evidence_seed"]["package_name"]
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "package_name" in exc.value.missing


def test_build_plan_raises_seed_incomplete_missing_versions_range():
    """SeedIncomplete raised when affected_versions_range is missing."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["evidence_seed"]["affected_versions_range"]
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "affected_versions_range" in exc.value.missing


def test_build_plan_raises_seed_incomplete_blank_cve():
    """SeedIncomplete raised when candidate_cve_id is blank."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    hyp["evidence_seed"]["candidate_cve_id"] = ""
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "candidate_cve_id" in exc.value.missing


def test_build_plan_raises_seed_incomplete_blank_package_name():
    """SeedIncomplete raised when package_name is blank."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    hyp["evidence_seed"]["package_name"] = "  "
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "package_name" in exc.value.missing


def test_build_plan_collects_all_missing_at_once():
    """SeedIncomplete collects ALL missing fields in one raise (not just the first)."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["evidence_seed"]["package_name"]
    del hyp["evidence_seed"]["candidate_cve_id"]
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "package_name" in exc.value.missing
    assert "candidate_cve_id" in exc.value.missing
    assert len(exc.value.missing) >= 2


def test_build_plan_raises_seed_incomplete_missing_version():
    """SeedIncomplete raised when target.version_or_revision is missing."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["target"]["version_or_revision"]
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "target.version_or_revision" in exc.value.missing


def test_build_plan_raises_seed_incomplete_blank_version():
    """SeedIncomplete raised when target.version_or_revision is empty string."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    hyp["target"]["version_or_revision"] = ""
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "target.version_or_revision" in exc.value.missing


def test_build_plan_raises_seed_incomplete_no_target():
    """SeedIncomplete raised when 'target' key is missing entirely."""
    strategy = _strategy()
    hyp = _minimatch_hypothesis()
    del hyp["target"]
    exc = pytest.raises(SeedIncomplete, strategy.build_plan, hyp)
    assert "target.version_or_revision" in exc.value.missing


# ---------------------------------------------------------------------------
# select_strategy('templated') now works (no longer ImportError)
# ---------------------------------------------------------------------------

def test_select_strategy_templated_returns_instance():
    """With templated.py implemented, select_strategy('templated') returns an instance."""
    from verify.strategy import select_strategy, PocStrategy
    from verify.templated import TemplatedPocStrategy
    result = select_strategy("templated")
    assert isinstance(result, TemplatedPocStrategy)
    assert isinstance(result, PocStrategy)
