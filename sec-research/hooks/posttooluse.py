#!/usr/bin/env python
"""PostToolUse dispatcher: PoT-1, PoT-2, PoT-3.

PoT-1: auto-tag new findings with Trace-ID (auto-correct, no block)
PoT-2: citation discipline check on finding.md (block if Fact:/Claim: lacks Citation:+Proof:)
PoT-3: timeline.md / evidence capture for runtime tool calls in active findings
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import (
    block, event_targets_workspace, find_active_override, is_in_workspace,
    passthrough, read_event, session_log,
)
from lib.paths import FINDINGS_DIR, RUNTIME_FEEDBACK_QUEUE


TRACE_ID_RE = re.compile(r"^FIND-\d{4}-\d{2}-\d{2}-\d{3}$")


def check_pot1_trace_id(event: dict) -> int | None:
    """PoT-1: auto-correct — if a new finding.md was just written without trace_id, inject one.

    This hook only WARNS at this stage (Stage 1); the actual auto-correct happens
    in finding.md frontmatter via verify_finding.py. PoT-1 logs an audit entry.
    """
    tool_name = event.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        return None
    tool_input = event.get("tool_input", {}) or {}
    fp = tool_input.get("file_path", "")
    if not fp or not is_in_workspace(fp):
        return None
    p = Path(fp).resolve()
    try:
        rel = p.relative_to(FINDINGS_DIR)
    except ValueError:
        return None
    if rel.name != "finding.md":
        return None

    # Best-effort: read content; check for trace_id in YAML frontmatter
    try:
        content = p.read_text(encoding="utf-8")
    except OSError:
        return None
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        if "trace_id:" in fm and TRACE_ID_RE.search(fm):
            return None  # Already has valid trace_id
    # Otherwise, log; don't block (PoT-1 is auto-correct, not block)
    session_log("pot1_missing_trace_id", {"file_path": fp})
    return None


def check_pot2_citation_discipline(event: dict) -> int | None:
    """PoT-2: every Fact:/Claim: line in finding.md must be followed by Citation: and Proof: lines."""
    tool_name = event.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return None
    tool_input = event.get("tool_input", {}) or {}
    fp = tool_input.get("file_path", "")
    if not fp or not is_in_workspace(fp):
        return None
    p = Path(fp).resolve()
    try:
        rel = p.relative_to(FINDINGS_DIR)
    except ValueError:
        return None
    if rel.name != "finding.md":
        return None

    try:
        content = p.read_text(encoding="utf-8")
    except OSError:
        return None

    # Strip frontmatter for the check
    body = re.sub(r"^---\n.*?\n---\n", "", content, count=1, flags=re.DOTALL)

    # Find every "Fact:" or "Claim:" line and check the next ~10 lines for Citation: and Proof:
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*\*\*?(Fact|Claim)\*\*?\s*:", line, re.IGNORECASE) or re.match(r"^\s*(Fact|Claim)\s*:", line, re.IGNORECASE):
            window = "\n".join(lines[i:i + 12])
            if not re.search(r"^\s*\*?\*?Citation\*?\*?\s*:", window, re.MULTILINE | re.IGNORECASE):
                override = find_active_override("PoT-2", f"{fp}:{i + 1}")
                if not override:
                    return block(
                        "PoT-2",
                        f"{fp}:{i + 1}",
                        "Fact/Claim line lacks 'Citation:' within 12 lines. Every claim must have a Tier-1 citation per citation-seeker rules.",
                        override_path=f"python scripts/sign_override.py --rule PoT-2",
                    )
            if not re.search(r"^\s*\*?\*?Proof\*?\*?\s*:", window, re.MULTILINE | re.IGNORECASE):
                override = find_active_override("PoT-2", f"{fp}:{i + 1}")
                if not override:
                    return block(
                        "PoT-2",
                        f"{fp}:{i + 1}",
                        "Fact/Claim line lacks 'Proof:' within 12 lines (cite source code snippet, command output, or HTTP trace).",
                        override_path=f"python scripts/sign_override.py --rule PoT-2",
                    )

    return None


def check_pot3_timeline_capture(event: dict) -> int | None:
    """PoT-3: runtime tool calls in active finding context must produce timeline entries.

    Stage 1 implementation: best-effort log to timeline.md if an active finding can be inferred
    from CWD or recent edits. If timeline.md write fails when it should succeed, block.
    """
    tool_name = event.get("tool_name", "")
    # Only act on Bash (potential PoC runs) and sandbox tools
    if tool_name != "Bash":
        return None
    tool_input = event.get("tool_input", {}) or {}
    cmd = tool_input.get("command", "") or ""

    # Heuristic: command mentions a finding's poc/ or runtime/ path
    finding_match = re.search(r"findings[\\/]([\w.-]+)[\\/]poc\b", cmd)
    if not finding_match:
        return None  # Not in active finding context
    finding_dir_name = finding_match.group(1)
    timeline_path = FINDINGS_DIR / finding_dir_name / "timeline.md"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    tool_response = event.get("tool_response", {}) or {}
    try:
        with timeline_path.open("a", encoding="utf-8") as f:
            f.write(f"\n## {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
            f.write(f"- Command: `{cmd[:200]}`\n")
            f.write(f"- Exit: {tool_response.get('exitCode', '?')}\n")
            stdout = tool_response.get("output", "") or ""
            if stdout:
                import hashlib
                f.write(f"- stdout-sha256: {hashlib.sha256(stdout.encode('utf-8', errors='ignore')).hexdigest()}\n")
    except OSError as exc:
        return block(
            "PoT-3",
            str(timeline_path),
            f"failed to write timeline: {exc}",
            override_path=f"python scripts/sign_override.py --rule PoT-3",
        )
    return None


def main() -> int:
    event = read_event()
    if not event:
        return passthrough()

    if not event_targets_workspace(event):
        return passthrough()

    for check in (check_pot1_trace_id, check_pot2_citation_discipline, check_pot3_timeline_capture):
        result = check(event)
        if result is not None:
            return result

    return passthrough()


if __name__ == "__main__":
    sys.exit(main())
