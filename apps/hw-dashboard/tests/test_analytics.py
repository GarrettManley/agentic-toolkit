"""Analytics tests — deterministic, fixture series, pure stdlib."""

from __future__ import annotations

from datetime import date

import pytest

from analytics import engine, signals
from collector import schema_io


# --- individual signals -----------------------------------------------------


def test_all_time_low_and_pct_above():
    prices = [450.0, 400.0, 420.0]
    assert signals.all_time_low(prices) == 400.0
    assert signals.pct_above_low(420.0, 400.0) == pytest.approx(0.05)


def test_percentile_rank_low_when_current_is_cheapest():
    prices = [500, 480, 460, 440, 420]
    # current == the minimum -> only 1 of 5 prices is <= it
    assert signals.percentile_rank(420, prices) == pytest.approx(0.2)


def test_ols_slope_matches_linear_ramp():
    prices = [100.0, 110.0, 120.0, 130.0, 140.0]
    slope, r2 = signals.ols_trend(prices)
    assert slope == pytest.approx(10.0)
    assert r2 == pytest.approx(1.0)
    assert signals.trend_direction(slope) == "rising"


def test_flat_series_reads_flat_within_deadband():
    prices = [400.0, 400.1, 399.9, 400.0]
    slope, _ = signals.ols_trend(prices)
    assert signals.trend_direction(slope) == "flat"


def test_rolling_median_ignores_one_day_spike():
    prices = [400, 400, 400, 1, 400, 400, 400]  # a single bad scrape
    assert signals.rolling_median(prices, 7) == 400
    assert signals.rolling_mean(prices, 7) != 400  # mean is corrupted; median is not


def test_confidence_is_monotonic_in_history():
    c2 = signals.confidence(2, 0)[0]
    c3 = signals.confidence(3, 0)[0]
    c14 = signals.confidence(14, 0)[0]
    c60 = signals.confidence(60, 0)[0]
    assert c2 <= c3 <= c14 <= c60
    assert signals.confidence(60, 0)[1] == "high"
    # seed-only history is capped at very_low
    assert signals.confidence(0, 30)[1] == "very_low"


# --- composite recommendation ----------------------------------------------


def test_buy_now_when_cheap_and_enough_history():
    rec = signals.recommend(
        percentile_rank_val=0.1,
        direction="flat",
        days_until_event=None,
        next_gen_launch=False,
        history_days=60,
        seed_days=0,
    )
    assert rec["signal"] == "buy_now"
    assert rec["confidence_label"] == "high"


def test_buy_now_suppressed_on_thin_history():
    rec = signals.recommend(
        percentile_rank_val=0.1,
        direction="flat",
        days_until_event=None,
        next_gen_launch=False,
        history_days=2,
        seed_days=0,
    )
    assert rec["signal"] == "watch"  # gated by very_low confidence


def test_wait_when_falling():
    rec = signals.recommend(
        percentile_rank_val=0.1,
        direction="falling",
        days_until_event=None,
        next_gen_launch=False,
        history_days=60,
        seed_days=0,
    )
    assert rec["signal"] == "wait"


def test_imminent_sale_event_defers_buy():
    rec = signals.recommend(
        percentile_rank_val=0.1,
        direction="flat",
        days_until_event=10,
        next_gen_launch=False,
        history_days=60,
        seed_days=0,
    )
    assert rec["signal"] == "watch"


# --- engine output ----------------------------------------------------------


def _series(prices, start_day=1):
    return [
        {
            "capture_date": f"2026-09-{start_day + i:02d}",
            "price": p,
            "currency": "USD",
            "retailer": "newegg",
        }
        for i, p in enumerate(prices)
    ]


def test_engine_output_validates_against_schema():
    rows = _series([450, 440, 430, 420, 410])
    record = engine.compute_analytics(
        sku_id="rtx-4060-ti-16gb-asus",
        component_id="rtx-4060-ti-16gb",
        series_rows=rows,
        today=date(2026, 9, 15),
    )
    ok, errors = schema_io.validate("analytics", record)
    assert ok, errors
    assert record["history_days"] == 5
    assert record["historical"]["all_time_low"] == 410
    assert any("weak" in c for c in record["caveats"])  # thin-data caveat present


def test_engine_handles_seed_only_history():
    seed = [
        {
            "capture_date": "2026-01-01",
            "price": 500,
            "currency": "USD",
            "source": "seed",
        }
    ]
    record = engine.compute_analytics(
        sku_id="x",
        component_id=None,
        series_rows=[],
        seed_rows=seed,
        today=date(2026, 9, 15),
    )
    ok, errors = schema_io.validate("analytics", record)
    assert ok, errors
    assert record["history_days"] == 0
    assert record["seed_days"] == 1
    assert record["recommendation"]["confidence_label"] == "very_low"
