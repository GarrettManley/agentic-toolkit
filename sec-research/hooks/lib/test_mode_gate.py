"""Shared --test-mode-confirm gate for sign_approval.py and sign_override.py.

Each of those scripts has a `--test-mode-confirm` CLI flag that skips its interactive
human-typed confirmation step, so tests can invoke them non-interactively. Left
unguarded, that flag is a live bypass of the human confirmation step it exists to
protect -- a token minted via the flag is signed identically to one minted through a
genuine confirmation, and no hook anywhere enforces anything on these scripts'
invocations (see docs/superpowers/specs/2026-07-01-discovery-loop-validation-design.md
§3). This gate closes that: the flag only takes effect when PYTEST_CURRENT_TEST is
present in the environment -- a marker pytest sets automatically for the duration of a
test run, and one that subprocess.run(...) (without an explicit env= override) inherits
automatically. Outside a pytest process, the marker is absent, so the flag is refused.
"""
from __future__ import annotations

import os


def test_mode_confirm_allowed() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))
