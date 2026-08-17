"""Curated achievements and their unlock predicates.

Each badge is a tiny record pairing display text with a pure predicate over the
ledger. Keeping the predicate as data (a ``Callable``) means new badges are added
declaratively, and :func:`newly_unlocked` handles the "unlock once" bookkeeping.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sprint.models import CLEARED_STATUSES, Ledger


@dataclass(frozen=True)
class BadgeDef:
    """A single achievement: identity, display text, and an unlock predicate."""

    id: str
    name: str
    description: str
    unlocked: Callable[[Ledger], bool]


def _cleared_count(ledger: Ledger) -> int:
    return sum(
        1 for record in ledger.modules.values() if record.status in CLEARED_STATUSES
    )


def _no_peek_count(ledger: Ledger) -> int:
    return sum(
        1
        for record in ledger.modules.values()
        if record.status in CLEARED_STATUSES and not record.peeked
    )


def _ruff_clean_count(ledger: Ledger) -> int:
    return sum(1 for record in ledger.modules.values() if record.ruff_clean)


def _module_cleared(ledger: Ledger, module_id: str) -> bool:
    record = ledger.modules.get(module_id)
    return record is not None and record.status in CLEARED_STATUSES


BADGES: tuple[BadgeDef, ...] = (
    BadgeDef(
        "first-green",
        "First Green",
        "Pass your first module.",
        lambda led: _cleared_count(led) >= 1,
    ),
    BadgeDef(
        "no-peek-novice",
        "No-Peek Novice",
        "Clear a module without revealing the solution.",
        lambda led: _no_peek_count(led) >= 1,
    ),
    BadgeDef(
        "ruff-rider",
        "Ruff Rider",
        "Three modules ruff-clean on first submit.",
        lambda led: _ruff_clean_count(led) >= 3,
    ),
    BadgeDef(
        "combo-breaker",
        "Combo Breaker",
        "Reach a x3 no-peek combo.",
        lambda led: led.combo >= 3,
    ),
    BadgeDef(
        "generator-guru",
        "Generator Guru",
        "Clear Module 04 (iterators & generators).",
        lambda led: _module_cleared(led, "04"),
    ),
    BadgeDef(
        "type-wrangler",
        "Type Wrangler",
        "Clear Module 06 (typing & errors).",
        lambda led: _module_cleared(led, "06"),
    ),
    BadgeDef(
        "test-pilot",
        "Test Pilot",
        "Clear Module 07 (testing & packaging).",
        lambda led: _module_cleared(led, "07"),
    ),
    BadgeDef(
        "streak-week",
        "Streak Week",
        "Maintain a 7-day streak.",
        lambda led: led.streak_days >= 7,
    ),
    BadgeDef(
        "centurion",
        "Centurion",
        "Earn 1000 XP.",
        lambda led: led.xp >= 1000,
    ),
    BadgeDef(
        "capstone-champion",
        "Capstone Champion",
        "Ship the capstone.",
        lambda led: _module_cleared(led, "capstone"),
    ),
)


def newly_unlocked(ledger: Ledger) -> list[BadgeDef]:
    """Badges whose predicate holds but which the ledger has not yet recorded."""
    owned = set(ledger.achievements)
    return [
        badge for badge in BADGES if badge.id not in owned and badge.unlocked(ledger)
    ]
