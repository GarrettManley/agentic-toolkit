"""Commit-SHA validation: confirm a SHA exists in a given repo.

Cache: runtime/cache/git/<owner>__<repo>__<sha>.json (indefinite TTL — SHAs are immutable).
Lookup: GitHub API (preferred) or `git ls-remote` fallback.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from .paths import RUNTIME_CACHE_GIT_DIR

# 7-40 hex chars
SHA_RE = re.compile(r"\b([a-f0-9]{7,40})\b")
GH_REPO_RE = re.compile(r"github\.com/([\w.-]+)/([\w.-]+)")


def _cache_path(owner: str, repo: str, sha: str) -> Path:
    return RUNTIME_CACHE_GIT_DIR / f"{owner}__{repo}__{sha}.json"


def _load_cache(owner: str, repo: str, sha: str) -> dict | None:
    p = _cache_path(owner, repo, sha)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(owner: str, repo: str, sha: str, data: dict) -> None:
    p = _cache_path(owner, repo, sha)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {**data, "_cached_at": time.time()}
    try:
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _query_github_api(owner: str, repo: str, sha: str) -> bool | None:
    """Try GitHub API. Returns True/False/None (None = unreachable)."""
    try:
        import urllib.request
        import urllib.error
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
        req = urllib.request.Request(url, headers={"User-Agent": "sec-research/1.0", "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 404 or e.code == 422:
                return False
            return None
    except Exception:
        return None
    return None


def _query_git_ls_remote(owner: str, repo: str, sha: str) -> bool | None:
    """Fallback: `git ls-remote` against the repo. Slower but works without API."""
    try:
        url = f"https://github.com/{owner}/{repo}.git"
        result = subprocess.run(
            ["git", "ls-remote", url, sha],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        # If the sha is a commit (not a ref), ls-remote won't match it directly.
        # Use a heuristic: if the output mentions the sha, it's a known ref-target.
        return sha in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def commit_exists(owner: str, repo: str, sha: str) -> tuple[bool, str | None]:
    """Confirm sha exists in github.com/<owner>/<repo>."""
    if not SHA_RE.fullmatch(sha):
        return False, f"malformed SHA: {sha}"

    cached = _load_cache(owner, repo, sha)
    if cached is not None and "exists" in cached:
        return cached["exists"], cached.get("reason")

    api_result = _query_github_api(owner, repo, sha)
    if api_result is True:
        _save_cache(owner, repo, sha, {"exists": True})
        return True, None
    if api_result is False:
        _save_cache(owner, repo, sha, {"exists": False, "reason": "GitHub API: commit not found"})
        return False, "commit not found in repo"

    # API failed; try git ls-remote
    fallback = _query_git_ls_remote(owner, repo, sha)
    if fallback is True:
        _save_cache(owner, repo, sha, {"exists": True})
        return True, None
    if fallback is False:
        _save_cache(owner, repo, sha, {"exists": False, "reason": "git ls-remote: not found"})
        return False, "commit not found in repo (ls-remote)"

    return False, "GitHub API and git ls-remote both unreachable; could not confirm"


def extract_repo_sha_pairs_from_text(text: str) -> list[tuple[str, str, str]]:
    """Find (owner, repo, sha) tuples where SHA is mentioned alongside a github.com/owner/repo URL.

    Heuristic: a SHA in the same line or paragraph as a github URL is treated as
    referring to that repo. Production-grade extraction would use a parser.
    """
    pairs: list[tuple[str, str, str]] = []
    repo_match = GH_REPO_RE.search(text)
    if not repo_match:
        return pairs
    owner, repo = repo_match.group(1), repo_match.group(2)
    for sha_match in SHA_RE.finditer(text):
        sha = sha_match.group(1)
        # Filter obvious false-positives (timestamps, version numbers in disguise)
        if len(sha) < 7:
            continue
        pairs.append((owner, repo, sha))
    return pairs
