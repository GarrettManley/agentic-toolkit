"""Shared utilities for hook dispatchers (pretooluse, posttooluse, stop, userpromptsubmit).

Each dispatcher:
1. Reads event JSON from stdin
2. Determines if the event is in-scope for sec-research/ (path-based + active-scope heuristic)
3. Runs applicable rules
4. Emits structured JSON violations to stderr; exits non-zero on first violation

Workspace-scope heuristic: hooks fire only when the tool input touches paths under
sec-research/, OR when the tool is HTTP/browser/fetch AND there is at least one
loaded program scope (i.e., active investigation work).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Need to add hooks/ to sys.path for the lib import to work when invoked as a script
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.paths import WORKSPACE_ROOT, OVERRIDES_SIGNED_DIR, OVERRIDES_USED_DIR, RUNTIME_SESSIONS_DIR  # noqa: E402
from lib.sign_verify import verify_token, is_expired, is_within_ceilings  # noqa: E402
from lib import ledger  # noqa: E402
from lib.scope_match import load_all_scopes  # noqa: E402

NETWORK_TOOLS = {
    "WebFetch", "WebSearch",
    "mcp__plugin_chrome-devtools-mcp_chrome-devtools__navigate_page",
    "mcp__plugin_chrome-devtools-mcp_chrome-devtools__new_page",
    "mcp__plugin_playwright_playwright__browser_navigate",
    "mcp__plugin_playwright_playwright__browser_network_request",
    "mcp__plugin_firecrawl_firecrawl",
}

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def read_event() -> dict[str, Any]:
    """Read hook event JSON from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def is_in_workspace(path_str: str) -> bool:
    """True if path resolves to a location inside sec-research/."""
    if not path_str:
        return False
    try:
        p = Path(path_str).resolve()
        return WORKSPACE_ROOT in p.parents or p == WORKSPACE_ROOT
    except (OSError, ValueError):
        return False


def event_targets_workspace(event: dict[str, Any]) -> bool:
    """Heuristic: does this event operate inside sec-research/?

    True if:
    - Edit/Write: file_path is inside sec-research/
    - Bash: command's first path argument is inside sec-research/
    - Network tool: at least one program scope is loaded (active investigation)
    """
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}

    # Edit/Write tools: check file_path
    if tool_name in EDIT_TOOLS:
        fp = tool_input.get("file_path", "")
        return is_in_workspace(fp)

    # Bash: check if cwd argument is inside, or if any path-argument is inside
    if tool_name == "Bash":
        cmd = tool_input.get("command", "") or ""
        # Quick heuristic: command mentions "sec-research" or runs from inside it
        if "sec-research" in cmd:
            return True
        # CWD is checked separately by the harness; we can't easily get it here

    # Network tools: trigger if any program scope is loaded
    if tool_name in NETWORK_TOOLS or tool_name.startswith("mcp__plugin_chrome-devtools-mcp"):
        scopes = load_all_scopes()
        return len(scopes) > 0

    return False


def find_active_override(rule_id: str, target: str | None) -> dict[str, Any] | None:
    """Look for a signed, unexpired, single-use-or-better override token for this rule_id.

    Marks token as used (moves to overrides/used/) if found and consumed.
    """
    if not OVERRIDES_SIGNED_DIR.exists():
        return None
    for token_path in OVERRIDES_SIGNED_DIR.glob("*.json"):
        try:
            with token_path.open("r", encoding="utf-8") as f:
                token = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if token.get("rule_id") != rule_id:
            continue
        ok, _err = verify_token(token)
        if not ok:
            continue
        if is_expired(token):
            continue
        ceil_ok, _ = is_within_ceilings(token)
        if not ceil_ok:
            continue
        # Optional: scope-target filtering
        if target:
            scope_target = token.get("scope", {}).get("target", "")
            if scope_target and scope_target != target and scope_target not in target:
                continue
        # Found — consume it
        max_uses = token.get("max_uses", 1)
        token.setdefault("_uses_count", 0)
        token["_uses_count"] += 1
        if token["_uses_count"] >= max_uses:
            # Move to used/
            OVERRIDES_USED_DIR.mkdir(parents=True, exist_ok=True)
            try:
                token_path.replace(OVERRIDES_USED_DIR / token_path.name)
                # Re-write with usage count
                with (OVERRIDES_USED_DIR / token_path.name).open("w", encoding="utf-8") as f:
                    json.dump(token, f, indent=2)
            except OSError:
                pass
        else:
            # Still has uses; persist count
            try:
                with token_path.open("w", encoding="utf-8") as f:
                    json.dump(token, f, indent=2)
            except OSError:
                pass
        # Log usage to ledger
        try:
            ledger.append_event(
                "override-used",
                override_token_id=token["token_id"],
                rule_id=rule_id,
                trace_id=token.get("scope", {}).get("trace_id"),
                notes=f"target={target}",
            )
        except Exception:
            pass
        return token
    return None


def block(rule_id: str, target: str, reason: str, override_path: str | None = "signed-token") -> int:
    """Emit a structured violation to stderr and return exit code 2 (block)."""
    payload = {
        "rule_id": rule_id,
        "action": "block",
        "target": target,
        "reason": reason,
        "override_path": override_path,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    sys.stderr.write(json.dumps(payload) + "\n")
    return 2


def passthrough() -> int:
    """Hook allows the action."""
    return 0


def session_log(event_type: str, details: dict[str, Any]) -> None:
    """Best-effort write to runtime/sessions/<date>.jsonl. Failure is non-fatal at this layer
    (S-2 hook will catch persistent failure)."""
    RUNTIME_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    line = json.dumps({
        "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_type": event_type,
        **details,
    }, ensure_ascii=False) + "\n"
    try:
        with (RUNTIME_SESSIONS_DIR / f"{today}.jsonl").open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
