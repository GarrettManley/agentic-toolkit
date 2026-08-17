"""Module 00 -- environment smoke test.

Fill in ``python_version()`` so the tests pass, then run this file directly to
see a short report confirming your toolchain is ready:

    uv run python modules/00-setup/check.py
"""

from __future__ import annotations

import platform


def python_version() -> tuple[int, int]:
    """Return the running interpreter's ``(major, minor)`` version.

    TODO: return the major and minor numbers from ``sys.version_info`` (it has
    ``.major`` and ``.minor`` attributes). You will need to ``import sys``.
    """
    raise NotImplementedError


def environment_report() -> dict[str, str]:
    major, minor = python_version()
    return {
        "python": f"{major}.{minor}",
        "implementation": platform.python_implementation(),
    }


if __name__ == "__main__":
    for key, value in environment_report().items():
        print(f"{key:<16} {value}")
