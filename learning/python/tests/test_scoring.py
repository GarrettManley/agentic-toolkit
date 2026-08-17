from datetime import date

from sprint import scoring
from sprint.models import Ledger, ModuleRecord, SkillMastery


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


def test_clear_quality_spans_the_full_range():
    assert scoring.clear_quality(no_peek=True, review_score=3) == 1.0
    assert scoring.clear_quality(no_peek=False, review_score=0) == scoring.QUALITY_FLOOR


def test_review_score_dominates_the_quality_signal():
    """The review must move mastery far more than merely clearing does.

    Regression guard: an earlier formula gave the review only 20% of the weight
    *and* applied mastery again at clear time, so the whole 0/3..3/3 rubric spanned
    4 percentage points and ``sprint next`` could not pick a real weakest skill.
    """
    worst = scoring.clear_quality(no_peek=True, review_score=0)
    best = scoring.clear_quality(no_peek=True, review_score=3)
    assert best - worst >= 0.7


def test_first_observation_seeds_mastery_directly():
    ledger = Ledger()
    scoring.apply_mastery(ledger, ["equality"], no_peek=True, review_score=3)
    assert ledger.skills["equality"].mastery == 1.0


def test_weak_review_pulls_mastery_down():
    ledger = Ledger()
    scoring.apply_mastery(ledger, ["comprehensions"], no_peek=True, review_score=3)
    peak = ledger.skills["comprehensions"].mastery
    scoring.apply_mastery(ledger, ["comprehensions"], no_peek=True, review_score=1)
    assert ledger.skills["comprehensions"].mastery < peak


def test_repeated_strong_reviews_converge_upward():
    ledger = Ledger()
    for _ in range(5):
        scoring.apply_mastery(ledger, ["unpacking"], no_peek=True, review_score=3)
    assert ledger.skills["unpacking"].mastery == 1.0


def test_mastery_stays_within_bounds():
    ledger = Ledger()
    for score in (0, 3, 0, 3, 1):
        scoring.apply_mastery(ledger, ["typing"], no_peek=False, review_score=score)
        assert 0.0 <= ledger.skills["typing"].mastery <= 1.0


def test_recompute_mastery_replays_records_in_completion_order():
    ledger = Ledger()
    ledger.modules["01"] = ModuleRecord(
        "01", status="cleared", review_score=3, completed_on="2026-08-17"
    )
    ledger.modules["02"] = ModuleRecord(
        "02", status="cleared", review_score=1, completed_on="2026-08-18"
    )
    ledger.skills["stale"] = SkillMastery("stale", 0.99)

    scoring.recompute_mastery(
        ledger, {"01": ["equality"], "02": ["comprehensions"]}.get
    )

    assert "stale" not in ledger.skills  # rebuilt from scratch, not merged
    assert ledger.skills["equality"].mastery == 1.0
    assert ledger.skills["comprehensions"].mastery == scoring.clear_quality(
        no_peek=True, review_score=1
    )


def test_recompute_mastery_ignores_unreviewed_modules():
    ledger = Ledger()
    ledger.modules["01"] = ModuleRecord("01", status="passed", review_score=None)
    scoring.recompute_mastery(ledger, {"01": ["equality"]}.get)
    assert ledger.skills == {}
