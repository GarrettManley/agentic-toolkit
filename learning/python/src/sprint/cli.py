"""``sprint`` command-line interface: the gamified progress tool.

Run it from the tutorial root (``learning/python``):

    uv run sprint status
    uv run sprint done 01
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from sprint import achievements, catalog, render, scoring, store
from sprint.models import CLEARED_STATUSES, Ledger, ModuleRecord


def _force_utf8() -> None:
    """Make stdout/stderr UTF-8 so any non-ASCII output survives the console."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def _project_root() -> Path:
    """Nearest ancestor (or cwd) containing ``pyproject.toml``."""
    here = Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return here


def _ledger_path(root: Path) -> Path:
    return root / ".sprint" / "ledger.json"


def _module_dir(root: Path, module_id: str) -> Path | None:
    matches = sorted((root / "modules").glob(f"{module_id}-*"))
    return matches[0] if matches else None


def _solution_file(root: Path, module_id: str) -> Path | None:
    matches = sorted((root / "solutions").glob(f"{module_id}-*.py"))
    return matches[0] if matches else None


def _run(cmd: list[str], cwd: Path) -> bool:
    """Run ``cmd`` in ``cwd``; return True on a zero exit code."""
    return subprocess.run(cmd, cwd=cwd).returncode == 0


def _cmd_done(root: Path, module_id: str, ledger: Ledger) -> int:
    try:
        spec = catalog.get(module_id)
    except KeyError:
        print(f"sprint: unknown module {module_id!r}")
        return 1

    mod_dir = _module_dir(root, module_id)
    if mod_dir is None:
        print(f"sprint: module {module_id} is not built yet.")
        return 1

    record = ledger.modules.setdefault(module_id, ModuleRecord(module_id))
    if record.status in CLEARED_STATUSES:
        print(f"sprint: module {module_id} already cleared ({record.xp_awarded} XP).")
        return 0

    record.attempts += 1
    if not _run([sys.executable, "-m", "pytest", str(mod_dir), "-q"], root):
        store.save(_ledger_path(root), ledger)
        print(f"sprint: {module_id} tests are still red -- make them pass, then rerun.")
        return 1

    ruff_ok = _run(["ruff", "check", str(mod_dir)], root)
    no_peek = not record.peeked
    ledger.combo = scoring.next_combo(ledger.combo, no_peek=no_peek)
    gained = scoring.module_xp(
        spec.base_xp,
        no_peek=no_peek,
        ruff_clean=ruff_ok,
        review_score=record.review_score,
        combo=ledger.combo,
    )
    ledger.xp += gained
    streak_xp = scoring.register_active_day(ledger, date.today())
    scoring.apply_mastery(
        ledger, spec.skills, no_peek=no_peek, review_score=record.review_score
    )

    record.status = "passed"
    record.ruff_clean = ruff_ok
    record.xp_awarded = gained
    record.completed_on = date.today().isoformat()

    unlocked = achievements.newly_unlocked(ledger)
    ledger.achievements.extend(badge.id for badge in unlocked)
    store.save(_ledger_path(root), ledger)

    streak_note = f" (+{streak_xp} streak)" if streak_xp else ""
    print(f"Module {module_id} cleared!  +{gained} XP{streak_note}")
    print(
        f"  no-peek: {'yes' if no_peek else 'no'}   "
        f"ruff-clean: {'yes' if ruff_ok else 'no'}   combo: x{ledger.combo}"
    )
    for badge in unlocked:
        print(f"  unlocked: {badge.name}")
    name, _floor, _next = scoring.level_for(ledger.xp)
    print(f"  total: {ledger.xp} XP ({name}).")
    print(f"  then ask for a review:  sprint review {module_id} --score N")
    return 0


def _cmd_reveal(root: Path, module_id: str, ledger: Ledger) -> int:
    solution = _solution_file(root, module_id)
    if solution is None:
        print(f"sprint: no reference solution for {module_id}.")
        return 1
    record = ledger.modules.setdefault(module_id, ModuleRecord(module_id))
    record.peeked = True
    store.save(_ledger_path(root), ledger)
    print(f"--- reference: {solution.name} (peek recorded) ---\n")
    print(solution.read_text(encoding="utf-8"))
    return 0


def _cmd_review(root: Path, module_id: str, score: int, ledger: Ledger) -> int:
    record = ledger.modules.get(module_id)
    if record is None or record.status not in CLEARED_STATUSES:
        print(f"sprint: clear module {module_id} before reviewing it.")
        return 1
    if record.review_score is not None:
        print(f"sprint: {module_id} already reviewed ({record.review_score}/3).")
        return 0

    record.review_score = score
    record.status = "cleared"
    bonus = scoring.REVIEW_UNIT * score
    ledger.xp += bonus
    record.xp_awarded += bonus
    scoring.apply_mastery(
        ledger,
        catalog.get(module_id).skills,
        no_peek=not record.peeked,
        review_score=score,
    )
    unlocked = achievements.newly_unlocked(ledger)
    ledger.achievements.extend(badge.id for badge in unlocked)
    store.save(_ledger_path(root), ledger)

    print(f"Recorded review {score}/3 for module {module_id}.  +{bonus} XP")
    for badge in unlocked:
        print(f"  unlocked: {badge.name}")
    return 0


def _cmd_next(root: Path, ledger: Ledger) -> int:
    for spec in catalog.built_modules():
        record = ledger.modules.get(spec.id)
        if record is None or record.status == "available":
            print(f"Next: Module {spec.id} - {spec.title}")
            print(f"  uv run pytest modules/{spec.id}-* -v")
            print(f"  then: uv run sprint done {spec.id}")
            return 0
    if ledger.skills:
        weakest = min(ledger.skills.values(), key=lambda skill: skill.mastery)
        print(
            f"All built modules cleared. Weakest skill: {weakest.skill_id} "
            f"({weakest.mastery:.0%}). Ask for a reinforcement module."
        )
    else:
        print("All built modules cleared. Ask for the next module.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sprint", description="Gamified Python Fluency Sprint tracker."
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="show the dashboard")
    done = sub.add_parser("done", help="score a module you have made green")
    done.add_argument("module")
    reveal = sub.add_parser("reveal", help="show a reference solution (records a peek)")
    reveal.add_argument("module")
    review = sub.add_parser("review", help="record an idiomatic-review score (0-3)")
    review.add_argument("module")
    review.add_argument("--score", type=int, required=True, choices=range(4))
    sub.add_parser("skills", help="per-skill mastery meters")
    sub.add_parser("achievements", help="badges earned and locked")
    sub.add_parser("next", help="what to do (or reinforce) next")
    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    args = _build_parser().parse_args(argv)
    root = _project_root()
    ledger = store.load(_ledger_path(root))

    if args.command in (None, "status"):
        print(render.status_screen(ledger))
        return 0
    if args.command == "done":
        return _cmd_done(root, args.module, ledger)
    if args.command == "reveal":
        return _cmd_reveal(root, args.module, ledger)
    if args.command == "review":
        return _cmd_review(root, args.module, args.score, ledger)
    if args.command == "skills":
        print(render.skills_screen(ledger))
        return 0
    if args.command == "achievements":
        print(render.achievements_screen(ledger))
        return 0
    return _cmd_next(root, ledger)
