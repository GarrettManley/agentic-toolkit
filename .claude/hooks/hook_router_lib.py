"""Pure functions for the Workspace hook federation router. No sys.exit, no global I/O
beyond reading child settings/config. Unit-testable in isolation."""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

# Corporate-isolation policy, enforced in code (NOT user-overridable).
HARD_EXCLUDES: tuple[str, ...] = ("Duracell*", "malachite")

_DEFAULT_CONFIG = {"enabled": True, "ignore": [], "timeout_seconds": 15}


@dataclass(frozen=True)
class Project:
    dir: Path
    settings: dict


def load_config(path: Path) -> dict:
    """Read the router config, falling back to defaults on missing/invalid file."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(_DEFAULT_CONFIG)
    return {**_DEFAULT_CONFIG, **(data if isinstance(data, dict) else {})}


def _excluded(name: str, user_ignore: list[str]) -> bool:
    if any(fnmatch.fnmatch(name, pat) for pat in HARD_EXCLUDES):
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in user_ignore)


def discover_projects(root: Path, config: dict) -> list[Project]:
    """Depth-1 scan for <child>/.claude/settings.json, minus corporate + user excludes."""
    user_ignore = config.get("ignore", []) or []
    projects: list[Project] = []
    try:
        children = sorted(p for p in Path(root).iterdir() if p.is_dir())
    except OSError:
        return projects
    for child in children:
        if _excluded(child.name, user_ignore):
            continue
        settings_path = child / ".claude" / "settings.json"
        if not settings_path.is_file():
            continue
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # a child with broken settings is skipped, not fatal
        projects.append(Project(dir=child, settings=settings))
    return projects


def matcher_matches(matcher: str | None, tool_name: str) -> bool:
    """Claude matchers are regexes over tool_name. Empty / '*' / '.*' mean match-all.
    A malformed regex matches nothing (and is the child's config bug, not ours)."""
    if not matcher or matcher in ("*", ".*"):
        return True
    try:
        return re.search(matcher, tool_name) is not None
    except re.error:
        return False


def resolve_command(command: str, child_dir: Path) -> list[str]:
    """Substitute ${CLAUDE_PROJECT_DIR} -> child dir (forward slashes) and split to argv.
    Commands MUST use forward slashes (backslashes are escape characters in POSIX mode).
    ${CLAUDE_PROJECT_DIR} always expands to a forward-slash path via as_posix(), so real
    child hooks are safe. Quoted paths with spaces (e.g. "C:/Program Files/x/hook.py")
    are handled correctly by posix=True."""
    substituted = command.replace("${CLAUDE_PROJECT_DIR}", Path(child_dir).as_posix())
    return shlex.split(substituted, posix=True)


def run_child_hook(argv: list[str], child_dir: Path, stdin_bytes: bytes,
                   timeout: float) -> tuple[int, str, str]:
    """Invoke one child hook with the replayed event on stdin. Returns (rc, stdout, stderr).
    Spawn failure / timeout is fail-open (rc 0) with a diagnostic on stderr — a router-side
    fault must not block the user's action; only a child's deliberate exit-2 blocks."""
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(child_dir)}
    try:
        proc = subprocess.run(argv, input=stdin_bytes, capture_output=True,
                              env=env, cwd=str(child_dir), timeout=timeout)
    except FileNotFoundError as e:
        return 0, "", f"[hook_router] child not runnable {argv!r}: {e}\n"
    except subprocess.TimeoutExpired:
        return 0, "", f"[hook_router] child timed out ({timeout}s): {argv!r}\n"
    except OSError as e:
        return 0, "", f"[hook_router] child spawn error {argv!r}: {e}\n"
    return (proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def aggregate(event_name: str, results: list[tuple[int, str, str]]) -> tuple[int, str, str]:
    """First child exit-2 blocks (forward its stderr). Otherwise exit 0; concatenate all
    child stdout (e.g. UserPromptSubmit injected context) and non-empty stderr (diagnostics).

    `event_name` is reserved for future per-event aggregation semantics (v1 treats every
    event identically); it is intentionally unused, not dead-by-accident."""
    for rc, _out, err in results:
        if rc == 2:
            return 2, "", err
    out = "".join(r[1] for r in results)
    err = "".join(r[2] for r in results if r[2])
    return 0, out, err


def timeout_for(config: dict, event_name: str) -> float:
    """Per-child timeout: `event_timeouts[event_name]` if set, else `timeout_seconds`.

    Stop needs headroom for children that typecheck (Roleplaying's deferred_typecheck
    allows itself 60 s); a flat 15 s killed them mid-run and dropped their errors."""
    overrides = config.get("event_timeouts") or {}
    return overrides.get(event_name, config.get("timeout_seconds", 15))


def route_event(stdin_bytes: bytes, root: Path, config: dict) -> tuple[int, str, str]:
    """Parse the event and run every matching child hook concurrently.

    Concurrent so an event costs the slowest child, not the sum (multi-agent runs fire
    Stop constantly). Results keep discovery order, so `aggregate` still lets the first
    child (in that order) that exits 2 win. Children are no longer skipped after a block:
    they already run in parallel, and federated hooks are guards, not side effects."""
    try:
        event = json.loads(stdin_bytes.decode("utf-8")) if stdin_bytes.strip() else {}
    except (ValueError, UnicodeDecodeError):
        return 0, "", ""  # can't parse -> fail open
    event_name = event.get("hook_event_name", "")
    tool_name = event.get("tool_name", "")
    timeout = timeout_for(config, event_name)

    jobs: list[tuple[list[str], Path]] = []
    for proj in discover_projects(root, config):
        for entry in (proj.settings.get("hooks", {}).get(event_name) or []):
            if not matcher_matches(entry.get("matcher"), tool_name):
                continue
            for h in (entry.get("hooks") or []):
                command = h.get("command")
                if command:
                    jobs.append((resolve_command(command, proj.dir), proj.dir))
    if len(jobs) <= 1:
        results = [run_child_hook(argv, d, stdin_bytes, timeout) for argv, d in jobs]
    else:
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            results = list(pool.map(
                lambda job: run_child_hook(job[0], job[1], stdin_bytes, timeout), jobs))
    return aggregate(event_name, results)
