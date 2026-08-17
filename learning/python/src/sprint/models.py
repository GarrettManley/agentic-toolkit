"""Persistent data model for the sprint progress engine.

These dataclasses are plain records — all behaviour lives in the sibling modules
(``scoring``, ``achievements``, ``store``) so the data stays trivially
serialisable to and from JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModuleRecord:
    """One module's outcome for the learner."""

    module_id: str
    status: str = "available"  # available -> passed -> cleared
    attempts: int = 0
    peeked: bool = False
    ruff_clean: bool | None = None
    review_score: int | None = None  # 0..3, assigned during review
    xp_awarded: int = 0
    completed_on: str | None = None  # ISO date, set when first passed


@dataclass
class SkillMastery:
    """Rolling mastery estimate for one tagged skill, in ``[0.0, 1.0]``."""

    skill_id: str
    mastery: float = 0.0


@dataclass
class Ledger:
    """The learner's entire progress state (persisted as JSON)."""

    xp: int = 0
    combo: int = 0
    streak_days: int = 0
    last_active: str | None = None  # ISO date of the most recent scored action
    modules: dict[str, ModuleRecord] = field(default_factory=dict)
    skills: dict[str, SkillMastery] = field(default_factory=dict)
    achievements: list[str] = field(default_factory=list)


# Statuses that count as "the learner solved this module".
CLEARED_STATUSES = frozenset({"passed", "cleared"})
