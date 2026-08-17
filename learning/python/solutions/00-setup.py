"""Reference answer for Module 00. Attempt modules/00-setup/check.py first."""

from __future__ import annotations

import platform
import sys


def python_version() -> tuple[int, int]:
    return (sys.version_info.major, sys.version_info.minor)


def environment_report() -> dict[str, str]:
    major, minor = python_version()
    return {
        "python": f"{major}.{minor}",
        "implementation": platform.python_implementation(),
    }
