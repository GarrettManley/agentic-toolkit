"""Append-only ledger writer for submissions/ledger.jsonl.

All issuance events (override-issued, approval-issued, submission-* and status-transition)
go through this. Writes are atomic-ish (open in append mode, write+flush+fsync).
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import LEDGER_PATH, SUBMISSIONS_DIR

ENTRY_ID_RE = re.compile(r"^led-(\d{4})-(\d{2})-(\d{2})-(\d{3})$")


def _utc_now_isoz() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _next_entry_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    counter = 1
    if LEDGER_PATH.exists():
        with LEDGER_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                eid = rec.get("entry_id", "")
                m = ENTRY_ID_RE.fullmatch(eid)
                if m and f"{m.group(1)}-{m.group(2)}-{m.group(3)}" == today:
                    n = int(m.group(4))
                    if n >= counter:
                        counter = n + 1
    return f"led-{today}-{counter:03d}"


def append_event(event_type: str, **fields: Any) -> dict[str, Any]:
    """Append a ledger event. Caller must supply event_type-required fields per schema.

    Always sets entry_id, actor (default 'unknown'), logged_at automatically if not supplied.
    """
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "entry_id": fields.pop("entry_id", _next_entry_id()),
        "event_type": event_type,
        "actor": fields.pop("actor", os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"),
        "logged_at": fields.pop("logged_at", _utc_now_isoz()),
    }
    entry.update(fields)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n"
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    return entry


def read_all() -> list[dict[str, Any]]:
    """Read all ledger entries."""
    if not LEDGER_PATH.exists():
        return []
    out: list[dict[str, Any]] = []
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def find_by_trace(trace_id: str) -> list[dict[str, Any]]:
    return [e for e in read_all() if e.get("trace_id") == trace_id]
