from datetime import date

from sprint import scoring
from sprint.models import Ledger


def test_level_for_boundaries():
    assert scoring.level_for(0) == ("Novice", 0, 150)
    assert scoring.level_for(149) == ("Novice", 0, 150)
    assert scoring.level_for(150) == ("Apprentice", 150, 400)
    assert scoring.level_for(1800) == ("Maintainer", 1800, None)
    assert scoring.level_for(5000) == ("Maintainer", 1800, None)


def test_module_xp_base_only():
    xp = scoring.module_xp(
        100, no_peek=False, ruff_clean=False, review_score=None, combo=0
    )
    assert xp == 100


def test_module_xp_all_bonuses_no_combo():
    xp = scoring.module_xp(100, no_peek=True, ruff_clean=True, review_score=3, combo=1)
    assert xp == 220  # 100 + (40 + 20 + 60) * 1.0


def test_module_xp_combo_multiplier_is_capped():
    # bonus 40, combo 6 -> multiplier capped at 1.5 -> +60
    xp = scoring.module_xp(
        100, no_peek=True, ruff_clean=False, review_score=None, combo=6
    )
    assert xp == 160


def test_next_combo_increments_and_resets():
    assert scoring.next_combo(2, no_peek=True) == 3
    assert scoring.next_combo(5, no_peek=False) == 0


def test_register_active_day_awards_once_per_day():
    ledger = Ledger()
    assert scoring.register_active_day(ledger, date(2026, 8, 17)) == 10
    assert ledger.streak_days == 1
    assert ledger.xp == 10
    # same day again: no award, no change
    assert scoring.register_active_day(ledger, date(2026, 8, 17)) == 0
    assert ledger.xp == 10


def test_register_active_day_extends_and_resets_streak():
    ledger = Ledger()
    scoring.register_active_day(ledger, date(2026, 8, 17))
    scoring.register_active_day(ledger, date(2026, 8, 18))  # consecutive
    assert ledger.streak_days == 2
    scoring.register_active_day(ledger, date(2026, 8, 20))  # gap -> reset
    assert ledger.streak_days == 1


def test_apply_mastery_raises_toward_one():
    ledger = Ledger()
    scoring.apply_mastery(ledger, ["equality"], no_peek=False, review_score=None)
    assert ledger.skills["equality"].mastery == 0.5  # quality 0.5, from 0.0
