#!/usr/bin/env python
"""Stop dispatcher: S-1, S-2.

S-1: refuse stop if a finding was modified this session but is missing PoC/schema-valid
     frontmatter AND isn't marked status: draft-incomplete.
S-2: refuse stop if session log can't be written.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import block, find_active_override, passthrough, read_event, session_log
from lib.paths import FINDINGS_DIR, RUNTIME_SESSIONS_DIR


def _scan_session_modified_findings() -> list[Path]:
    """Heuristic: any finding.md modified in the last 30 minutes is a candidate.
    Stage 1 keeps it simple; later stages can read transcript_path for precise tracking."""
    if not FINDINGS_DIR.exists():
        return []
    threshold = datetime.now(timezone.utc).timestamp() - 30 * 60
    out: list[Path] = []
    for finding_md in FINDINGS_DIR.glob("**/finding.md"):
        try:
            mtime = finding_md.stat().st_mtime
        except OSError:
            continue
        if mtime > threshold:
            out.append(finding_md)
    return out


def _is_complete(finding_md: Path) -> tuple[bool, str | None]:
    """Check the finding has schema-valid frontmatter, PoC at expected path, and isn't draft-incomplete."""
    try:
        content = finding_md.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"unable to read: {exc}"
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return False, "missing YAML frontmatter"
    fm_text = fm_match.group(1)

    # If status is draft-incomplete, allow stop
    status_match = re.search(r"^status:\s*(\S+)", fm_text, re.MULTILINE)
    if status_match and status_match.group(1).strip("\"'").lower() == "draft-incomplete":
        return True, None

    # Otherwise must have PoC and required fields
    poc_path = finding_md.parent / "poc" / "reproduce.sh"
    if not poc_path.exists():
        return False, f"missing PoC at {poc_path}"

    # Must have a trace_id
    if "trace_id:" not in fm_text:
        return False, "missing trace_id in frontmatter"

    return True, None


def check_s1_completeness(event: dict) -> int | None:
    """S-1: refuse stop if any session-modified finding is incomplete and not draft-incomplete."""
    candidates = _scan_session_modified_findings()
    for finding_md in candidates:
        ok, err = _is_complete(finding_md)
        if ok:
            continue
        override = find_active_override("S-1", str(finding_md))
        if override:
            continue
        return block(
            "S-1",
            str(finding_md),
            f"session-modified finding is incomplete: {err}. Either complete it, mark status: draft-incomplete, or sign an override.",
            override_path=f"python sec-research/scripts/sign_override.py --rule S-1 --target {finding_md}",
        )
    return None


def check_s2_session_log(event: dict) -> int | None:
    """S-2: write session-end summary; block if write fails."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = RUNTIME_SESSIONS_DIR / f"{today}.jsonl"
    try:
        RUNTIME_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "event_type": "session_stop",
                "session_id": event.get("session_id", ""),
            }) + "\n")
    except OSError as exc:
        override = find_active_override("S-2", str(log_path))
        if override:
            return None
        return block(
            "S-2",
            str(log_path),
            f"failed to write session log: {exc}",
            override_path=f"python sec-research/scripts/sign_override.py --rule S-2",
        )
    return None


def main() -> int:
    event = read_event()
    # Stop hooks always fire regardless of workspace-targeting heuristic
    for check in (check_s1_completeness, check_s2_session_log):
        result = check(event)
        if result is not None:
            return result
    return passthrough()


if __name__ == "__main__":
    sys.exit(main())
