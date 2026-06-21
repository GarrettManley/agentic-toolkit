#!/usr/bin/env python
"""Workspace hook federation router.

Registered for PreToolUse / PostToolUse / Stop / UserPromptSubmit at the Workspace root.
Self-dispatches on hook_event_name, discovers nested projects' own .claude/settings.json,
and replays their matching hooks — so nested-project hooks fire from the hub root.

Fail-open on any router fault; only a child's deliberate exit-2 blocks (its stderr is
forwarded verbatim)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent           # .claude/hooks/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import hook_router_lib as lib  # noqa: E402

# ROOT must be the launch (Workspace) root. Prefer CLAUDE_PROJECT_DIR (the canonical
# project dir Claude Code sets at launch); fall back to the __file__-derived Workspace
# dir when unset (tests, manual runs). It must NOT point at a child dir — discovery
# would then scan the wrong tree.
ROOT = Path(os.environ["CLAUDE_PROJECT_DIR"]) if os.environ.get("CLAUDE_PROJECT_DIR") else _HERE.parent.parent
CONFIG_PATH = _HERE / "hook-router.config.json"


def main() -> int:
    raw = sys.stdin.buffer.read()
    try:
        config = lib.load_config(CONFIG_PATH)
        if not config.get("enabled", True):
            return 0
        rc, out, err = lib.route_event(raw, ROOT, config)
        if out:
            sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
        return rc
    except Exception as exc:                        # noqa: BLE001 — fail-open is the contract
        sys.stderr.write(f"[hook_router] internal error (passing through): {exc}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
