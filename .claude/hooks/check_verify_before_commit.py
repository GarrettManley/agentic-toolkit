"""PreToolUse hook: gate `git commit` at the Workspace root on the mandated
verification scripts.

GEMINI.md §3 ("Finality & Verification") requires `_scripts/pre_commit_audit.ps1`
and `_scripts/verify_workspace.ps1` to pass before work is declared complete. That
was documentation-only — nothing enforced it. This hook turns it into a hard block
at the natural completion boundary: the commit.

Behavior:
  - Allow immediately unless the command is a `git commit` (catches `commit --amend`).
  - Override valve: a `[verify-override: <reason>]` marker in the command OR the
    WORKSPACE_VERIFY_OVERRIDE env var bypasses the gate, with an auditable note.
  - Scope guard: if every staged path is under `sec-research/`, skip — that subtree
    has its own G-1..G-4 git hooks and double-gating is wasteful/confusing.
  - Run both scripts (blocking). Deny if either exits non-zero, surfacing the output
    tail + remediation + override instructions.
  - Fail OPEN on any internal error (no pwsh, timeout, git failure): a broken gate
    must never wedge every commit. Emits a warning instead.

Output contract mirrors the other ~/.claude PreToolUse hooks: JSON on stdout with
`hookSpecificOutput.permissionDecision`; always exit 0.

Hooks load at session start — edits here need a Claude Code restart to take effect.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# `git`, optional global flags (`-c x.y=z`, `-C path`), then `commit`.
# `git log`/`git status` don't match (the token after `git` is neither a flag
# nor `commit`). `\bcommit\b` also matches `commit --amend`.
_GIT_COMMIT = re.compile(r"\bgit\s+(?:-\S+\s+|--\S+\s+)*commit\b", re.IGNORECASE)

# Auditable, lightweight override. (HMAC parity with sec-research is a noted
# upgrade, not built here.)
_OVERRIDE_MARKER = re.compile(r"\[verify-override:\s*([^\]]+)\]", re.IGNORECASE)
_OVERRIDE_ENV = "WORKSPACE_VERIFY_OVERRIDE"

# Verification scripts, relative to the workspace root, in run order.
_SCRIPTS = ("_scripts/pre_commit_audit.ps1", "_scripts/verify_workspace.ps1")
_PER_SCRIPT_TIMEOUT_S = 12  # keep total under the hook's 30s ceiling


def _emit(decision: str, *, reason: str | None = None, note: str | None = None) -> None:
    output: dict[str, object] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
    }
    payload: dict[str, object] = {"hookSpecificOutput": output}
    if decision == "deny" and reason:
        output["permissionDecisionReason"] = reason
        payload["systemMessage"] = reason
    elif note:
        payload["systemMessage"] = note
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def _workspace_root() -> Path:
    # <root>/.claude/hooks/this_file.py -> parents[2] == <root>
    return Path(__file__).resolve().parents[2]


def _staged_paths(root: Path) -> list[str] | None:
    """Staged paths relative to the repo root, or None if git can't be queried."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def _run_script(root: Path, rel: str) -> tuple[int, str]:
    """(returncode, combined-output-tail). returncode -1 signals a run failure."""
    script = root / rel
    if not script.is_file():
        return (-1, f"script not found: {script}")
    try:
        proc = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(script)],
            capture_output=True, text=True, timeout=_PER_SCRIPT_TIMEOUT_S,
            cwd=str(root),
        )
    except FileNotFoundError:
        return (-1, "pwsh not found on PATH")
    except subprocess.TimeoutExpired:
        return (-1, f"{rel} timed out after {_PER_SCRIPT_TIMEOUT_S}s")
    except OSError as exc:
        return (-1, f"{rel} failed to launch: {exc}")
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if len(tail) > 1500:
        tail = "…" + tail[-1500:]
    return (proc.returncode, tail)


def _deny_reason(rel: str, tail: str) -> str:
    return (
        f"BLOCKED: workspace verification gate — `{rel}` failed before commit.\n\n"
        "GEMINI.md §3 requires the audit + workspace verification to pass before "
        "work is declared complete. Fix the reported issues and re-commit.\n\n"
        f"--- {rel} output (tail) ---\n{tail}\n"
        "---------------------------\n\n"
        "To bypass intentionally, append a reason marker to the commit command, e.g.\n"
        '   git commit -m "msg [verify-override: <why>]"\n'
        f"or set ${_OVERRIDE_ENV}=1 for the session (auditable; use sparingly)."
    )


def main() -> int:
    raw = ""
    with contextlib.suppress(Exception):
        raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        _emit("allow")
        return 0

    command = (event.get("tool_input") or {}).get("command") or ""
    if not isinstance(command, str) or not _GIT_COMMIT.search(command):
        _emit("allow")
        return 0

    # Override valve.
    marker = _OVERRIDE_MARKER.search(command)
    if marker:
        _emit("allow", note=f"⚠ Workspace verify gate OVERRIDDEN: {marker.group(1).strip()}")
        return 0
    if os.environ.get(_OVERRIDE_ENV):
        _emit("allow", note=f"⚠ Workspace verify gate OVERRIDDEN via ${_OVERRIDE_ENV}.")
        return 0

    root = _workspace_root()

    # Scope guard: let sec-research's own git hooks own a sec-research-only commit.
    staged = _staged_paths(root)
    if staged is not None:
        if not staged:
            _emit("allow")  # nothing staged; git will handle the empty commit
            return 0
        if all(p.startswith("sec-research/") for p in staged):
            _emit("allow", note="Workspace verify gate skipped: sec-research/-only "
                                 "commit (its own G-1..G-4 hooks apply).")
            return 0

    # Run the gate. Fail OPEN on any run failure (rc == -1) so a broken gate
    # cannot wedge all commits; only a real non-zero script exit denies.
    for rel in _SCRIPTS:
        rc, tail = _run_script(root, rel)
        if rc == -1:
            _emit("allow", note=f"⚠ Workspace verify gate could not run ({rel}): "
                                f"{tail}. Allowing commit — verify manually.")
            return 0
        if rc != 0:
            _emit("deny", reason=_deny_reason(rel, tail))
            return 0

    _emit("allow", note="✓ Workspace verification passed (audit + verify_workspace).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
