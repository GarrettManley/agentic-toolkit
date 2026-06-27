"""Run journal — the proof artifact for a supervised end-to-end run.

A single Markdown document per run at ``runtime/journals/<date>-<slug>.md``, written
incrementally — one section per checkpoint — as the supervised driver advances. Because
each section is flushed as it happens, an interrupted run's journal is honest about exactly
where it stopped, rather than looking complete.

Distinct from the hash-chained ledger (``submissions/ledger.jsonl``): the ledger is the
append-only machine audit of submission/override events; the journal is the human-readable
narrative of one run. It is what makes a *null* result defensible ("here is every hypothesis
and why each was refuted/deduped/errored") and a *draft* result auditable.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from lib.paths import RUNTIME_JOURNALS_DIR


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RunJournal:
    """Incremental Markdown journal for one supervised run.

    ``start()`` (re)writes the header; every other method appends and flushes, so the file
    on disk always reflects progress up to the last completed call.
    """

    def __init__(self, slug: str, *, date: str, journals_dir: Path | None = None) -> None:
        self.slug = slug
        self.date = date
        base = journals_dir if journals_dir is not None else RUNTIME_JOURNALS_DIR
        self.path = base / f"{date}-{slug}.md"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def start(self, *, program_reason: str) -> Path:
        """Write (clobbering) the journal header + program-selection rationale."""
        self.path.write_text(
            f"# Run Journal — {self.slug} ({self.date})\n\n"
            f"Started: {_utc_now_iso()}\n\n"
            f"## Program selection\n\n{program_reason}\n",
            encoding="utf-8",
        )
        return self.path

    def checkpoint(self, stage: str, *, outcome: str, detail: str = "") -> None:
        """Append a stage checkpoint section."""
        block = (
            f"\n## Checkpoint — {stage}\n\n"
            f"- Time: {_utc_now_iso()}\n"
            f"- Outcome: {outcome}\n"
        )
        if detail:
            block += f"\n{detail}\n"
        self._append(block)

    def note(self, text: str) -> None:
        """Append a free-form note (e.g. a live-reconcile gap and the fix applied)."""
        self._append(f"\n{text}\n")

    def finish(self, *, outcome: str) -> None:
        """Append the terminal outcome section."""
        self._append(
            f"\n## Outcome\n\n- Finished: {_utc_now_iso()}\n- Result: {outcome}\n"
        )

    def _append(self, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(text)
