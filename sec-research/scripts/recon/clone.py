"""Gated shallow clone of an in-scope repo. gate(url) fires BEFORE the git
subprocess (the subprocess-scope-gap mitigation). Only in-scope repos are cloned;
dependency source is not. Clone/size failures set skipped_reason and recon continues."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from recon._http import gate

CLONE_SIZE_CAP_MB = 500


@dataclass(frozen=True)
class CloneResult:
    cloned: bool
    clone_path: str | None = None
    commit_sha: str | None = None
    skipped_reason: str | None = None


def _dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def _repo_url(repo_identifier: str) -> str:
    # repo_identifier is the bare "github.com/<owner>/<repo>" form used in scopes.
    return f"https://{repo_identifier}" if not repo_identifier.startswith("http") else repo_identifier


def _slug(repo_identifier: str) -> str:
    parts = repo_identifier.rstrip("/").split("/")
    return f"{parts[-2]}-{parts[-1]}" if len(parts) >= 2 else parts[-1]


def clone_repo(repo_identifier: str, dest_root: Path, *,
               runner=subprocess.run) -> CloneResult:
    dest = dest_root / _slug(repo_identifier)
    url = _repo_url(repo_identifier)
    gate(url)  # raises ScopeViolation if blocked — propagates uncaught

    dest_root.mkdir(parents=True, exist_ok=True)
    proc = runner(["git", "clone", "--depth", "1", url, str(dest)],
                  capture_output=True, text=True)
    if getattr(proc, "returncode", 1) != 0:
        return CloneResult(cloned=False,
                           skipped_reason=f"clone failed: {getattr(proc, 'stderr', '')[:200]}".strip())

    if _dir_size_mb(dest) > CLONE_SIZE_CAP_MB:
        return CloneResult(cloned=False, clone_path=str(dest),
                           skipped_reason=f"size>{CLONE_SIZE_CAP_MB}MB cap")

    sha_proc = runner(["git", "-C", str(dest), "rev-parse", "HEAD"],
                      capture_output=True, text=True)
    sha = (getattr(sha_proc, "stdout", "") or "").strip() or None
    return CloneResult(cloned=True, clone_path=str(dest), commit_sha=sha)
