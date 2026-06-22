"""Pure price-signal functions over a chronologically-sorted price series.

Stdlib only (`statistics`). Each function is small and independently testable;
the engine composes them. Honest for short, growing series: confidence scales
with first-party history and `buy_now` is suppressed on thin data."""

from __future__ import annotations

import statistics
from datetime import date

# Annual sale events as (label, month, day) anchors (approximate; US calendar).
# next-gen launches are not here — they're passed in per-component as a flag.
SALE_EVENTS = [
    ("Prime Day", 7, 16),
    ("Black Friday", 11, 28),
    ("Cyber Monday", 12, 1),
]

TREND_DEADBAND_USD_PER_DAY = 0.25  # |slope| below this reads as flat


def all_time_low(prices: list[float]) -> float | None:
    return min(prices) if prices else None


def all_time_high(prices: list[float]) -> float | None:
    return max(prices) if prices else None


def pct_above_low(current: float, low: float | None) -> float | None:
    if low is None or low <= 0:
        return None
    return (current - low) / low


def percentile_rank(current: float, prices: list[float]) -> float | None:
    """Fraction of observed prices >= current (so a low current price -> low rank
    -> 'cheaper than most days')."""
    if not prices:
        return None
    at_or_below = sum(1 for p in prices if p <= current)
    return at_or_below / len(prices)


def _tail(values: list[float], n: int) -> list[float]:
    return values[-n:] if len(values) > n else values


def rolling_mean(prices: list[float], n: int) -> float | None:
    tail = _tail(prices, n)
    return statistics.fmean(tail) if tail else None


def rolling_median(prices: list[float], n: int) -> float | None:
    tail = _tail(prices, n)
    return statistics.median(tail) if tail else None


def stdev(prices: list[float]) -> float | None:
    return statistics.stdev(prices) if len(prices) >= 2 else None


def volatility(prices: list[float]) -> float | None:
    """Coefficient of variation (stdev / mean)."""
    if len(prices) < 2:
        return None
    mean = statistics.fmean(prices)
    return statistics.stdev(prices) / mean if mean else None


def ols_trend(prices: list[float]) -> tuple[float | None, float | None]:
    """Ordinary least-squares slope (usd per index step) + r^2 over the series.
    Returns (slope, r_squared); (None, None) if < 2 points or zero x-variance."""
    n = len(prices)
    if n < 2:
        return None, None
    xs = list(range(n))
    mx = statistics.fmean(xs)
    my = statistics.fmean(prices)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None, None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, prices))
    slope = sxy / sxx
    syy = sum((y - my) ** 2 for y in prices)
    r2 = (sxy * sxy) / (sxx * syy) if syy > 0 else 1.0
    return slope, r2


def trend_direction(slope: float | None) -> str:
    if slope is None:
        return "unknown"
    if slope <= -TREND_DEADBAND_USD_PER_DAY:
        return "falling"
    if slope >= TREND_DEADBAND_USD_PER_DAY:
        return "rising"
    return "flat"


def holt_forecast(
    prices: list[float], horizon: int = 7, alpha: float = 0.5, beta: float = 0.3
) -> float | None:
    """Holt double-exponential smoothing point forecast `horizon` steps ahead.
    Labeled low-confidence by the engine; needs >= 3 points."""
    if len(prices) < 3:
        return None
    level = prices[0]
    trend = prices[1] - prices[0]
    for p in prices[1:]:
        prev_level = level
        level = alpha * p + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
    return level + horizon * trend


def days_until_next_event(
    today: date, events=SALE_EVENTS
) -> tuple[str | None, int | None]:
    """Nearest upcoming sale event and days until it (searches this year + next)."""
    best_label, best_days = None, None
    for label, month, day in events:
        for year in (today.year, today.year + 1):
            try:
                ev = date(year, month, day)
            except ValueError:
                continue
            delta = (ev - today).days
            if delta >= 0 and (best_days is None or delta < best_days):
                best_label, best_days = label, delta
    return best_label, best_days


def confidence(history_days: int, seed_days: int) -> tuple[float, str]:
    """Confidence scales with first-party history; seed-only history is capped at
    'low'. Monotonic non-decreasing in history_days."""
    if history_days >= 60:
        return 0.85, "high"
    if history_days >= 14:
        return 0.6, "moderate"
    if history_days >= 3:
        return 0.3, "low"
    if history_days >= 1 or seed_days > 0:
        return 0.15, "very_low"
    return 0.0, "very_low"


def recommend(
    *,
    percentile_rank_val: float | None,
    direction: str,
    days_until_event: int | None,
    next_gen_launch: bool,
    history_days: int,
    seed_days: int,
) -> dict:
    """Composite best-time-to-buy signal. buy_now is gated by confidence so thin
    data never yields a confident buy."""
    rationale: list[str] = []
    if percentile_rank_val is None:
        signal = "watch"
        rationale.append("no price history yet")
    elif direction == "falling":
        signal = "wait"
        rationale.append("price is trending down — likely to fall further")
    elif percentile_rank_val <= 0.25:
        signal = "buy_now"
        rationale.append(
            f"current price is in the cheapest {round(percentile_rank_val * 100)}% of observed days"
        )
    elif percentile_rank_val >= 0.75:
        signal = "wait"
        rationale.append("current price is near the high end of its observed range")
    else:
        signal = "watch"
        rationale.append("price is mid-range for its observed history")

    if (
        days_until_event is not None
        and 0 <= days_until_event <= 21
        and signal == "buy_now"
    ):
        signal = "watch"
        rationale.append(f"a major sale event is {days_until_event} days away")

    if next_gen_launch and signal == "buy_now":
        signal = "watch"
        rationale.append("a next-gen launch is expected to push prior-gen prices down")

    conf, label = confidence(history_days, seed_days)
    if signal == "buy_now" and label in ("very_low", "low"):
        signal = "watch"
        rationale.append(
            f"not enough history ({history_days}d) to recommend buying with confidence"
        )

    return {
        "signal": signal,
        "confidence": conf,
        "confidence_label": label,
        "rationale": rationale,
    }
