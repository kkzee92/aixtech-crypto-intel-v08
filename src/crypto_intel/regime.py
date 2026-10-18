"""Shared market-regime classifier for asset-class research rules (v0.8 multi-scale notes).

Enhanced with volatility context and adaptive thresholds.
"""

from __future__ import annotations

from enum import Enum
from statistics import fmean

from crypto_intel.models import Candle


class Regime(str, Enum):
    TREND = "trend"
    RANGE = "range"
    STRESS = "stress"


class VolatilityTier(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


def atr_pct(candles: list[Candle], bars: int = 8) -> float:
    window = candles[-bars:]
    ranges = [(c.high - c.low) / c.close for c in window if c.close]
    return fmean(ranges) if ranges else 0.0


def volatility_tier(candles: list[Candle]) -> VolatilityTier:
    width = atr_pct(candles)
    if width >= 0.04:
        return VolatilityTier.HIGH
    if width <= 0.015:
        return VolatilityTier.LOW
    return VolatilityTier.NORMAL


def classify(candles: list[Candle]) -> Regime:
    """Stress first, then trend versus range. Research label, not a forecast.
    Multi-scale notes available via longer windows in strategies.
    """
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    width = atr_pct(candles)
    stress_thresh = 0.032 if volatility_tier(candles) is VolatilityTier.HIGH else 0.035
    if width >= stress_thresh:
        return Regime.STRESS
    closes = [c.close for c in candles]
    span = closes[-1] / closes[-8] - 1.0
    trend_thresh = 0.022 if volatility_tier(candles) is VolatilityTier.LOW else 0.025
    if abs(span) >= trend_thresh:
        return Regime.TREND
    return Regime.RANGE
