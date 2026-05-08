#!/usr/bin/env python
"""PreToolUse dispatcher: PT-1 through PT-6.

Reads hook event JSON from stdin. Exits 2 with structured stderr message on block.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# common.py adds hooks/ to sys.path for lib imports
from common import (
    EDIT_TOOLS, NETWORK_TOOLS,
    block, event_targets_workspace, find_active_override, is_in_workspace,
    passthrough, read_event, session_log,
)
from lib.paths import WORKSPACE_ROOT, SUBMISSIONS_TOKENS_DIR, FINDINGS_DIR
from lib.scope_match import host_in_scope, is_in_scope, load_all_scopes
from lib.nvd_lookup import validate_cve_ids_in_text
from lib.registry_lookup import extract_pkg_versions, version_exists
from lib.git_lookup import extract_repo_sha_pairs_from_text, commit_exists
from lib.secret_scan import scan_text


SUBMISSION_VENUE_HOSTS = {
    "api.huntr.com", "huntr.com",
    "api.github.com",  # gh api for ghsa
    "api.hackerone.com", "hackerone.com",
    "api.bugcrowd.com", "bugcrowd.com",
    "api.intigriti.com", "intigriti.com",
}

SUBMIT_SCRIPT_PATTERNS = [
    r"\bscripts[\\/]submit\.py\b",
    r"\bsec-research[\\/]scripts[\\/]submit\.py\b",
]


def _command_invokes_submit_py(cmd: str) -> bool:
    return any(re.search(p, cmd, re.IGNORECASE) for p in SUBMIT_SCRIPT_PATTERNS)


def _approval_token_provided(cmd: str) -> str | None:
    m = re.search(r"--(?:approval-)?token(?:[=\s])\s*([A-Za-z0-9-]+)", cmd)
    return m.group(1) if m else None


def _approval_token_valid(token_id: str, trace_id: str | None) -> tuple[bool, str | None]:
    """PT-2: Check approval token is signed, present, and matches trace_id."""
    p = SUBMISSIONS_TOKENS_DIR / f"{token_id}.json"
    if not p.exists():
        return False, f"approval token not found: {token_id}"
    try:
        from lib.sign_verify import verify_token, is_expired
        with p.open("r", encoding="utf-8") as f:
            token = json.load(f)
        ok, err = verify_token(token)
        if not ok:
            return False, f"approval token verification failed: {err}"
        if is_expired(token):
            return False, "approval token expired"
        if trace_id and token.get("trace_id") != trace_id:
            return False, f"approval token trace_id mismatch (token={token.get('trace_id')}, requested={trace_id})"
        return True, None
    except Exception as exc:
        return False, f"failed to load approval token: {exc}"


def check_pt1_scope(event: dict) -> int | None:
    """PT-1: HTTP/browser/fetch must hit hosts in loaded scope."""
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}

    target_url = None
    if tool_name == "WebFetch":
        target_url = tool_input.get("url", "")
    elif tool_name == "WebSearch":
        # WebSearch is broad; we don't restrict it — only specific URL fetches
        return None
    elif tool_name in NETWORK_TOOLS or tool_name.startswith("mcp__plugin_chrome-devtools-mcp") or tool_name.startswith("mcp__plugin_playwright"):
        target_url = tool_input.get("url") or tool_input.get("urlOrPath", "")
    elif tool_name == "Bash":
        # Heuristic: extract URL from curl/wget commands
        cmd = tool_input.get("command", "") or ""
        m = re.search(r"\b(?:curl|wget|http)[^\n]*?(https?://[^\s'\"]+)", cmd, re.IGNORECASE)
        if m:
            target_url = m.group(1)

    if not target_url:
        return None

    in_scope, prog = host_in_scope(target_url)
    if in_scope:
        return None

    override = find_active_override("PT-1", urlparse(target_url).hostname or target_url)
    if override:
        return None

    return block(
        "PT-1",
        target_url,
        f"target host not in any loaded program scope. Load a program first via load_program.py, or sign an override.",
        override_path=f"python sec-research/scripts/sign_override.py --rule PT-1 --target {urlparse(target_url).hostname}",
    )


def check_pt2_submission(event: dict) -> int | None:
    """PT-2: submission requires approval token. NO override path."""
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}

    cmd = tool_input.get("command", "") or "" if tool_name == "Bash" else ""
    target_url = ""
    if tool_name == "WebFetch":
        target_url = tool_input.get("url", "")
    elif tool_name in NETWORK_TOOLS:
        target_url = tool_input.get("url", "")

    invokes_submit = tool_name == "Bash" and _command_invokes_submit_py(cmd)
    is_venue_call = False
    if target_url:
        host = (urlparse(target_url).hostname or "").lower()
        is_venue_call = any(host == v or host.endswith("." + v) for v in SUBMISSION_VENUE_HOSTS)

    if not (invokes_submit or is_venue_call):
        return None

    # If invoking submit.py, must have --token <id>
    if invokes_submit:
        tok = _approval_token_provided(cmd)
        if not tok:
            return block(
                "PT-2",
                "submit.py invocation",
                "submit.py requires --token <approval-token-id>. Generate via sign_approval.py.",
                override_path=None,
            )
        # Optional: check trace_id consistency
        trace_m = re.search(r"--trace\s+(FIND-[\d-]+)", cmd)
        trace_id = trace_m.group(1) if trace_m else None
        ok, err = _approval_token_valid(tok, trace_id)
        if not ok:
            return block("PT-2", "submit.py invocation", err or "invalid approval token", override_path=None)

    if is_venue_call:
        # Direct venue API call from non-submit.py path is suspicious. Block unless approval token present.
        # (This catches e.g. Bash curl to api.huntr.com)
        return block(
            "PT-2",
            target_url,
            "Direct submission-venue API call detected outside of submit.py. Use submit.py with --token.",
            override_path=None,
        )

    return None


def check_pt3_path(event: dict) -> int | None:
    """PT-3: Edit/Write must target paths inside sec-research/."""
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}
    if tool_name not in EDIT_TOOLS:
        return None
    fp = tool_input.get("file_path", "")
    if not fp:
        return None
    if is_in_workspace(fp):
        return None

    override = find_active_override("PT-3", fp)
    if override:
        return None

    return block(
        "PT-3",
        fp,
        "file path resolves outside sec-research/. Hooks only authorize edits within the workspace.",
        override_path=f"python sec-research/scripts/sign_override.py --rule PT-3 --target {fp}",
    )


def check_pt4_fab_refs(event: dict) -> int | None:
    """PT-4: writes to findings/**.md must have verifiable CVE/pkg/SHA refs."""
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}
    if tool_name not in EDIT_TOOLS:
        return None
    fp = tool_input.get("file_path", "")
    if not fp or not is_in_workspace(fp):
        return None
    p = Path(fp).resolve()
    try:
        rel = p.relative_to(FINDINGS_DIR)
    except ValueError:
        return None  # Not in findings/
    if not rel.name.endswith(".md"):
        return None

    # Get the new content (what's being written)
    new_content = tool_input.get("content") or tool_input.get("new_string") or ""
    if not new_content:
        return None

    # Validate CVE IDs
    cve_failures = validate_cve_ids_in_text(new_content)
    if cve_failures:
        cve_id, err = cve_failures[0]
        override = find_active_override("PT-4", cve_id)
        if not override:
            return block(
                "PT-4",
                cve_id,
                f"CVE ID validation failed: {err}",
                override_path=f"python sec-research/scripts/sign_override.py --rule PT-4 --target {cve_id}",
            )

    # Validate package@version (best-effort: ecosystem inferred from finding's frontmatter
    # in a real implementation. For now, attempt npm/pypi).
    pkg_versions = extract_pkg_versions(new_content)
    for pkg, ver in pkg_versions:
        # Try ecosystems in order; if any registry confirms, accept
        confirmed = False
        for ecosystem in ("npm", "pypi", "cargo", "rubygems"):
            try:
                ok, _err = version_exists(ecosystem, pkg, ver)
                if ok:
                    confirmed = True
                    break
            except NotImplementedError:
                continue
        if not confirmed:
            override = find_active_override("PT-4", f"{pkg}@{ver}")
            if not override:
                return block(
                    "PT-4",
                    f"{pkg}@{ver}",
                    f"package {pkg}@{ver} not found in any supported registry (npm/pypi/cargo/rubygems)",
                    override_path=f"python sec-research/scripts/sign_override.py --rule PT-4 --target {pkg}@{ver}",
                )

    # Validate commit SHAs (only if a github.com/owner/repo is also mentioned)
    repo_sha_pairs = extract_repo_sha_pairs_from_text(new_content)
    for owner, repo, sha in repo_sha_pairs:
        ok, err = commit_exists(owner, repo, sha)
        if not ok:
            override = find_active_override("PT-4", sha)
            if not override:
                return block(
                    "PT-4",
                    f"github.com/{owner}/{repo}@{sha}",
                    f"commit SHA validation failed: {err}",
                    override_path=f"python sec-research/scripts/sign_override.py --rule PT-4 --target {sha}",
                )

    return None


def check_pt5_sandbox(event: dict) -> int | None:
    """PT-5: PoC code / registry installs must go through sandbox_server.py."""
    tool_name = event.get("tool_name", "")
    if tool_name != "Bash":
        return None
    tool_input = event.get("tool_input", {}) or {}
    cmd = tool_input.get("command", "") or ""

    # Patterns that indicate "running PoC" or "installing from registry"
    risky_patterns = [
        (r"\bnpm\s+install\b", "npm install"),
        (r"\bpip\s+install\b", "pip install"),
        (r"\byarn\s+add\b", "yarn add"),
        (r"\bpnpm\s+add\b", "pnpm add"),
        (r"\bcargo\s+install\b", "cargo install"),
        (r"\bgem\s+install\b", "gem install"),
        (r"\bbash\s+poc/reproduce\.sh\b", "PoC reproduce"),
        (r"\bsh\s+poc/reproduce\.sh\b", "PoC reproduce"),
        (r"\b\./poc/reproduce\.sh\b", "PoC reproduce"),
    ]
    for pattern, desc in risky_patterns:
        if re.search(pattern, cmd):
            # Allow if the command is being invoked via sandbox_server
            if "sandbox_server" in cmd or "docker" in cmd.lower():
                return None
            override = find_active_override("PT-5", desc)
            if override:
                return None
            return block(
                "PT-5",
                desc,
                f"command must execute via sandbox_server.py (Docker isolation), not directly. Pattern: {pattern}",
                override_path=f"python sec-research/scripts/sign_override.py --rule PT-5 --target {desc!r}",
            )
    return None


def check_pt6_secrets(event: dict) -> int | None:
    """PT-6: Edit/Write to evidence/redacted/ must not contain secrets. NO override."""
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}
    if tool_name not in EDIT_TOOLS:
        return None
    fp = tool_input.get("file_path", "")
    if not fp:
        return None
    p = Path(fp).resolve()
    try:
        rel = p.relative_to(FINDINGS_DIR)
    except ValueError:
        return None
    rel_str = str(rel).replace("\\", "/")
    if "/evidence/redacted/" not in rel_str:
        return None

    new_content = tool_input.get("content") or tool_input.get("new_string") or ""
    if not new_content:
        return None
    matches = scan_text(new_content)
    if matches:
        m = matches[0]
        return block(
            "PT-6",
            f"{fp}:{m.line_number}",
            f"secret detected in evidence/redacted/: pattern={m.pattern_name}; redact before committing.",
            override_path=None,
        )
    return None


def main() -> int:
    event = read_event()
    if not event:
        return passthrough()

    if not event_targets_workspace(event):
        return passthrough()

    session_log("pretooluse", {"tool_name": event.get("tool_name", "")})

    for check in (check_pt1_scope, check_pt2_submission, check_pt3_path, check_pt4_fab_refs, check_pt5_sandbox, check_pt6_secrets):
        result = check(event)
        if result is not None:
            return result

    return passthrough()


if __name__ == "__main__":
    sys.exit(main())
