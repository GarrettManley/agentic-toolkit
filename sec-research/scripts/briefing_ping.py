"""briefing_ping.py — cloud-side companion to nightly.py.

Reads the latest runtime/briefings/<date>.md and emits a short notification
(stdout in Stage 1; can be wired to email/push/Slack later). Designed to be
registered via the `schedule` skill (RemoteTrigger) ~30 min after nightly's
typical completion window.

This script never needs local filesystem access in production — for cloud-side
use, the briefing artifact would be synced to an accessible store first. Stage 1
keeps it local and prints to stdout so the pipeline is testable end-to-end.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from lib.paths import RUNTIME_BRIEFINGS_DIR  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Ping a notification with the latest briefing summary.")
    p.add_argument("--date", help="Specific date YYYY-MM-DD (default: today)")
    p.add_argument("--quiet", action="store_true", help="Suppress full briefing body; just print path")
    args = p.parse_args()

    target_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    briefing_path = RUNTIME_BRIEFINGS_DIR / f"{target_date}.md"

    if not briefing_path.exists():
        print(f"No briefing for {target_date} at {briefing_path}", file=sys.stderr)
        # Fallback: most recent briefing
        if RUNTIME_BRIEFINGS_DIR.exists():
            candidates = sorted(RUNTIME_BRIEFINGS_DIR.glob("*.md"))
            if candidates:
                print(f"Most recent: {candidates[-1].name}", file=sys.stderr)
        return 1

    print(f"=== Briefing: {briefing_path} ===")
    if not args.quiet:
        print(briefing_path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
