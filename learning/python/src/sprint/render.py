"""Pure rendering of ledger state to plain-text screens.

Output is deliberately ASCII so it survives any console encoding; the CLI also
forces UTF-8 stdout as a belt-and-braces measure.
"""

from __future__ import annotations

from sprint import achievements, catalog, scoring
from sprint.models import CLEARED_STATUSES, Ledger

_WIDTH = 32


def bar(frac: float, width: int = 10) -> str:
    """A ``####------`` progress bar for ``frac`` clamped to ``[0, 1]``."""
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * width)
    return "#" * filled + "-" * (width - filled)


def _cleared_built(ledger: Ledger) -> int:
    return sum(
        1
        for spec in catalog.built_modules()
        if spec.id in ledger.modules
        and ledger.modules[spec.id].status in CLEARED_STATUSES
    )


def status_screen(ledger: Ledger) -> str:
    """The main dashboard: level, module progress, streak, and badges."""
    name, floor, next_floor = scoring.level_for(ledger.xp)
    level_no = scoring.level_number(name)
    built = catalog.built_modules()
    cleared = _cleared_built(ledger)

    lines = ["Python Fluency Sprint", "-" * _WIDTH]
    if next_floor is None:
        lines.append(f"Lv.{level_no} {name}   {ledger.xp} XP (max)")
    else:
        into, span = ledger.xp - floor, next_floor - floor
        lines.append(f"Lv.{level_no} {name}   {bar(into / span)}  {ledger.xp} XP")
        lines.append(f"  next level at {next_floor} XP")

    lines.append(
        f"Modules   {bar(cleared / len(built))}  {cleared}/{len(built)} built cleared"
    )
    lines.append(f"Streak    {ledger.streak_days} day(s)    Combo x{ledger.combo}")
    if ledger.achievements:
        lines.append(f"Badges    {len(ledger.achievements)} earned")
    return "\n".join(lines)


def skills_screen(ledger: Ledger) -> str:
    """Per-skill mastery meters, or a nudge when nothing is tracked yet."""
    if not ledger.skills:
        return "No skills tracked yet -- clear a module to start building mastery."
    lines = ["Skill mastery", "-" * _WIDTH]
    for skill_id in sorted(ledger.skills):
        mastery = ledger.skills[skill_id].mastery
        lines.append(f"  {skill_id:<18} {bar(mastery)}  {mastery:.0%}")
    return "\n".join(lines)


def achievements_screen(ledger: Ledger) -> str:
    """Every badge with an earned/locked marker."""
    owned = set(ledger.achievements)
    lines = ["Achievements", "-" * _WIDTH]
    for badge in achievements.BADGES:
        mark = "[x]" if badge.id in owned else "[ ]"
        lines.append(f"  {mark} {badge.name} -- {badge.description}")
    return "\n".join(lines)
