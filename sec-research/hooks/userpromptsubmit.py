#!/usr/bin/env python
"""UserPromptSubmit dispatcher: UPS-1, UPS-2.

UPS-1: if prompt mentions testing/recon/exploit and no scope is loaded, inject reminder.
UPS-2: if prompt names hosts/URLs/packages/repos that don't resolve to a loaded scope, block.

Note: UserPromptSubmit hooks can inject context via stdout (per Claude Code spec).
A non-zero exit code rejects the prompt.
"""
from __future__ import annotations

import re
import sys

from common import block, find_active_override, passthrough, read_event
from lib.scope_match import extract_targets_from_text, is_in_scope, load_all_scopes


TESTING_KEYWORDS_RE = re.compile(
    r"\b(?:exploit|recon|enumerate|payload|fuzz|sqlmap|brute|attack|inject|test\s+(?:against|the))\b",
    re.IGNORECASE,
)


def check_ups1_scope_reminder(event: dict) -> int | None:
    """UPS-1: testing-keyword prompts with no scope loaded → inject reminder via stdout."""
    prompt = event.get("prompt", "") or ""
    if not TESTING_KEYWORDS_RE.search(prompt):
        return None
    scopes = load_all_scopes()
    if scopes:
        return None  # At least one scope loaded; no reminder needed
    # Inject reminder (non-blocking)
    sys.stdout.write(
        "\n[sec-research/UPS-1 reminder] Your prompt suggests testing or recon work, but no program scope is currently loaded. "
        "Load a program first: `python sec-research/scripts/load_program.py --venue <v> --identifier <id>`. "
        "Hooks will hard-block out-of-scope HTTP and ambiguous targets until a scope is active.\n"
    )
    return None


def check_ups2_ambiguous_targets(event: dict) -> int | None:
    """UPS-2: any URL/host/package/repo in the prompt must resolve to a loaded scope."""
    prompt = event.get("prompt", "") or ""
    targets = extract_targets_from_text(prompt)
    if not targets:
        return None

    scopes = load_all_scopes()
    if not scopes:
        # If no scopes are loaded, UPS-1 already injected a reminder. Don't double-block here.
        return None

    for asset_type, identifier in targets:
        in_scope, _ = is_in_scope(asset_type, identifier)
        if in_scope:
            continue
        override = find_active_override("UPS-2", identifier)
        if override:
            continue
        return block(
            "UPS-2",
            identifier,
            f"prompt references {asset_type}={identifier!r} which doesn't resolve to a loaded scope. Load the program first or sign an override.",
            override_path=f"python sec-research/scripts/sign_override.py --rule UPS-2 --target {identifier}",
        )
    return None


def main() -> int:
    event = read_event()
    if not event:
        return passthrough()
    for check in (check_ups1_scope_reminder, check_ups2_ambiguous_targets):
        result = check(event)
        if result is not None:
            return result
    return passthrough()


if __name__ == "__main__":
    sys.exit(main())
