"""XP, levels, combo, streak, and mastery math.

Kept as small functions over explicit inputs (including an injected ``today``) so
the whole module is deterministic and unit-testable — a habit worth copying.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from sprint.models import Ledger, SkillMastery

LEVELS: tuple[tuple[str, int], ...] = (
    ("Novice", 0),
    ("Apprentice", 150),
    ("Journeyman", 400),
    ("Pythonista", 800),
    ("Core Dev", 1300),
    ("Maintainer", 1800),
)

NO_PEEK_BONUS = 40
RUFF_BONUS = 20
REVIEW_UNIT = 20  # XP per idiomatic-review point (score is 0..3)
STREAK_XP = 10
_COMBO_CAP = 1.5


def level_for(xp: int) -> tuple[str, int, int | None]:
    """Return ``(name, floor, next_floor)`` for ``xp``.

    ``floor`` is the XP threshold of the current level; ``next_floor`` is the
    threshold of the next level, or ``None`` at the top.
    """
    name, floor = LEVELS[0]
    next_floor: int | None = LEVELS[1][1]
    for index, (level_name, level_floor) in enumerate(LEVELS):
        if xp >= level_floor:
            name, floor = level_name, level_floor
            next_floor = LEVELS[index + 1][1] if index + 1 < len(LEVELS) else None
    return name, floor, next_floor


def level_number(name: str) -> int:
    """1-based position of a level name in :data:`LEVELS` (1 if unknown)."""
    for index, (level_name, _floor) in enumerate(LEVELS):
        if level_name == name:
            return index + 1
    return 1


def module_xp(
    base: int,
    *,
    no_peek: bool,
    ruff_clean: bool,
    review_score: int | None,
    combo: int,
) -> int:
    """Total XP for clearing a module, applying bonuses and the combo multiplier.

    The combo multiplier scales only the *bonus* portion (not the base), so a
    streak of clean, no-peek clears compounds without runaway inflation.
    """
    bonus = (
        (NO_PEEK_BONUS if no_peek else 0)
        + (RUFF_BONUS if ruff_clean else 0)
        + REVIEW_UNIT * (review_score or 0)
    )
    multiplier = min(_COMBO_CAP, 1 + 0.1 * max(0, combo - 1))
    return base + round(bonus * multiplier)


def next_combo(previous: int, *, no_peek: bool) -> int:
    """Grow the no-peek combo, or reset it to zero when the learner peeked."""
    return previous + 1 if no_peek else 0


def register_active_day(ledger: Ledger, today: date) -> int:
    """Record activity on ``today``; return the streak XP awarded (0 or STREAK_XP).

    Repeated actions on the same day do not re-award. A clear exactly one day
    after the last extends the streak; any longer gap resets it to one day.
    """
    iso = today.isoformat()
    if ledger.last_active == iso:
        return 0
    yesterday = (today - timedelta(days=1)).isoformat()
    ledger.streak_days = (
        ledger.streak_days + 1 if ledger.last_active == yesterday else 1
    )
    ledger.last_active = iso
    ledger.xp += STREAK_XP
    return STREAK_XP


def apply_mastery(
    ledger: Ledger,
    skills: Iterable[str],
    *,
    no_peek: bool,
    review_score: int | None,
) -> None:
    """Raise each tagged skill's mastery toward 1.0, weighted by clear quality."""
    quality = 0.5 + (0.3 if no_peek else 0.0) + 0.2 * ((review_score or 0) / 3)
    for skill_id in skills:
        current = ledger.skills.get(skill_id, SkillMastery(skill_id))
        current.mastery = round(current.mastery + quality * (1.0 - current.mastery), 3)
        ledger.skills[skill_id] = current
