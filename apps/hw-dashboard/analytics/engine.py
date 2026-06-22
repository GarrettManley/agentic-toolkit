"""Compose price signals into one analytics record per SKU.

Merges first-party series with seed history (seed flagged for confidence capping),
computes signals, and emits a dict validating against analytics.schema.json."""

from __future__ import annotations

from datetime import date, datetime, timezone

from analytics import signals

ENGINE_VERSION = "engine@1"


def compute_analytics(
    *,
    sku_id: str,
    component_id: str | None,
    series_rows: list[dict],
    seed_rows: list[dict] | None = None,
    next_gen_launch: bool = False,
    today: date | None = None,
) -> dict:
    """Build the analytics record. `series_rows` = first-party snapshots,
    `seed_rows` = backfilled history. Both are dicts with capture_date + price."""
    seed_rows = seed_rows or []
    today = today or datetime.now(timezone.utc).date()

    first_party = sorted(series_rows, key=lambda r: r["capture_date"])
    merged = sorted([*seed_rows, *series_rows], key=lambda r: r["capture_date"])
    prices = [float(r["price"]) for r in merged]

    history_days = len({r["capture_date"] for r in first_party})
    seed_days = len({r["capture_date"] for r in seed_rows})

    current_row = first_party[-1] if first_party else (merged[-1] if merged else None)
    current = {
        "price": float(current_row["price"]) if current_row else 0.0,
        "currency": (current_row or {}).get("currency", "USD"),
        "retailer": (current_row or {}).get("retailer"),
        "captured_at": (current_row or {}).get("captured_at"),
        "in_stock": (current_row or {}).get("in_stock"),
    }

    low = signals.all_time_low(prices)
    high = signals.all_time_high(prices)
    cur_price = current["price"]
    pctile = signals.percentile_rank(cur_price, prices) if prices else None
    low_date = (
        next((r["capture_date"] for r in merged if float(r["price"]) == low), None)
        if low is not None
        else None
    )

    slope, r2 = signals.ols_trend(prices)
    direction = signals.trend_direction(slope)
    event_label, days_until = signals.days_until_next_event(today)

    rec = signals.recommend(
        percentile_rank_val=pctile,
        direction=direction,
        days_until_event=days_until,
        next_gen_launch=next_gen_launch,
        history_days=history_days,
        seed_days=seed_days,
    )

    caveats: list[str] = []
    if history_days < 14:
        caveats.append(
            f"based on {history_days} day(s) of first-party tracking — forecast is weak"
        )
    if seed_days and not history_days:
        caveats.append(
            "only seeded third-party history available; first-party tracking not started"
        )

    record = {
        "sku_id": sku_id,
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine_version": ENGINE_VERSION,
        "history_days": history_days,
        "seed_days": seed_days,
        "data_points": len(merged),
        "current": current,
        "historical": {
            "all_time_low": low,
            "all_time_low_date": low_date,
            "all_time_high": high,
            "pct_above_low": signals.pct_above_low(cur_price, low),
            "percentile_rank": pctile,
        },
        "rolling": {
            "mean_7d": signals.rolling_mean(prices, 7),
            "median_7d": signals.rolling_median(prices, 7),
            "mean_30d": signals.rolling_mean(prices, 30),
            "median_30d": signals.rolling_median(prices, 30),
            "stdev_30d": signals.stdev(signals._tail(prices, 30)),
            "volatility": signals.volatility(prices),
        },
        "trend": {
            "usd_per_day": slope,
            "direction": direction,
            "holt_forecast_7d": signals.holt_forecast(prices),
            "r_squared": r2,
        },
        "events": {
            "nearest_event": event_label,
            "days_until": days_until,
            "next_gen_launch_flag": next_gen_launch,
            "note": "",
        },
        "recommendation": rec,
        "caveats": caveats,
    }
    if component_id is not None:
        record["component_id"] = component_id
    return record
