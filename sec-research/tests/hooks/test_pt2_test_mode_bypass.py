"""Tests for hook-level enforcement of the --test-mode-confirm gate (design §3, layered
defense alongside lib/test_mode_gate.py's env-var check): a Bash command that directly
invokes sign_approval.py or sign_override.py with --test-mode-confirm must be blocked
unconditionally, with no override -- an ordinary env var is not a secret, so a
self-attested check inside the gated process alone can always be spoofed.
"""
from __future__ import annotations


def _bash_event(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_direct_sign_override_invocation_with_flag_is_blocked():
    import pretooluse
    event = _bash_event(
        "python scripts/sign_override.py --rule PT-1 --target x "
        "--reason 'trying to bypass confirmation directly' --test-mode-confirm"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is not None


def test_direct_sign_approval_invocation_with_flag_is_blocked():
    import pretooluse
    event = _bash_event(
        "python scripts/sign_approval.py FIND-2026-07-01-001 --venue huntr --test-mode-confirm"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is not None


def test_spoofed_env_var_prefix_does_not_evade_the_hook():
    """The env-var spoofing attempt itself: prefixing the command with a fake
    PYTEST_CURRENT_TEST does not help, because the hook matches on the script+flag
    pair in the command text, not on any environment state."""
    import pretooluse
    event = _bash_event(
        "PYTEST_CURRENT_TEST=fake python scripts/sign_override.py --rule PT-1 "
        "--target x --reason 'spoofed env var attempt' --test-mode-confirm"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is not None


def test_pytest_invocation_itself_is_not_blocked():
    """A real pytest run's own Bash command text never contains --test-mode-confirm
    literally -- pytest's internal subprocess.run(...) call builds that argument list
    at runtime, invisible to this hook. This must NOT be blocked."""
    import pretooluse
    event = _bash_event(
        "pytest tests/scripts/test_sign_override_test_mode_gate.py "
        "tests/hooks/test_override_singleuse.py -v"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is None


def test_unrelated_command_is_not_blocked():
    import pretooluse
    event = _bash_event("git status")
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is None


def test_cwd_relative_invocation_with_flag_is_blocked():
    """The evasion this fix closes: invoking the bare filename after cd'ing into
    scripts/ must not slip past the path-qualified patterns."""
    import pretooluse
    event = _bash_event(
        "cd scripts && python sign_override.py --rule PT-1 --target x "
        "--reason 'cwd-relative evasion attempt' --test-mode-confirm"
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is not None


def test_flag_without_a_confirmation_script_is_not_blocked():
    """--test-mode-confirm only matters in the context of sign_approval.py/
    sign_override.py -- an unrelated command that happens to contain the same
    substring (e.g. in commit-message prose) must not be blocked (avoids the
    known command-string-overmatch class of bug this workspace has hit before)."""
    import pretooluse
    event = _bash_event(
        'git commit -m "docs: mention --test-mode-confirm in a changelog entry"'
    )
    result = pretooluse.check_pt2_test_mode_bypass(event)
    assert result is None
