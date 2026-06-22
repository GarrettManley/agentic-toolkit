"""Translate a Windows host path to the /mnt/<drive>/... form WSL2 docker mounts expect."""
from __future__ import annotations

import re
from pathlib import Path

_DRIVE_RE = re.compile(r"^([A-Za-z]):/(.*)$")


def win_to_wsl(path: Path | str) -> str:
    s = str(path).replace("\\", "/")  # normalize separators first
    m = _DRIVE_RE.match(s)
    if not m:
        return s  # already POSIX-ish; pass through
    drive, rest = m.group(1).lower(), m.group(2)
    return f"/mnt/{drive}/{rest}"
