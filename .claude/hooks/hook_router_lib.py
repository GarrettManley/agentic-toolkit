"""Pure functions for the Workspace hook federation router. No sys.exit, no global I/O
beyond reading child settings/config. Unit-testable in isolation."""
from __future__ import annotations

import fnmatch
import json
import re
import shlex
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
    posix=True is correct here because commands use forward slashes by convention."""
    substituted = command.replace("${CLAUDE_PROJECT_DIR}", Path(child_dir).as_posix())
    return shlex.split(substituted, posix=True)
