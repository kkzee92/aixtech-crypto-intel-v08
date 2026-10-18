"""Asset-class strategy research rules.

Enhanced multi-factor heuristics with multi-scale regimes, Bollinger-style channels, ADX-like trend strength, adaptive volatility thresholds, MACD, and tighter filters for paper research (v0.8).
Not forecasts and not a recommendation to trade. Each class has an entry, an invalidation, regime and vol overlay.
"""

from __future__ import annotations

from statistics import fmean, pstdev

from crypto_intel.models import AssetClass, Candle, Side, Signal
from crypto_intel.regime import Regime, VolatilityTier, classify, volatility_tier

PLAYBOOK: dict[AssetClass, dict[str, str]] = {
    AssetClass.MAJOR: {
        "hypothesis": "Liquid majors trend with multi-EMA, MACD, Bollinger channel confirmation, and ADX proxy when not in stress or high-vol mismatch.",
        "entry": "Fast > mid > slow EMA, rising MACD, price near or above mid Bollinger, ADX proxy > threshold, adaptive RSI.",
        "invalidation": "Stress, high-vol mismatch, or RSI stretched.",
        "horizon": "8 bars mean-reversion, 20 bars trend",
    },
    AssetClass.LARGE_CAP_ALT: {
        "hypothesis": "Volume-confirmed breakouts with multi-momentum, MACD, and Bollinger upper breach outside stress.",
        "entry": "Close above prior high and Bollinger upper, volume adaptive, positive momentum and MACD.",
        "invalidation": "Stress or missing multi-confirmation.",
        "horizon": "12 bars",
    },
    AssetClass.STABLECOIN: {
        "hypothesis": "Statistical peg deviation is the signal. Adaptive + z-score alerts only.",
        "entry": "Deviation or z-score beyond adaptive thresholds raises alert. No order.",
        "invalidation": "N/A. Size zero.",
        "horizon": "1 bar monitor",
    },
    AssetClass.DEFI: {
        "hypothesis": "Trend only in multi-scale calm non-stress with channel support and momentum.",
        "entry": "Close above EMA and mid-channel, realised vol adaptive, positive momentum, not stress.",
        "invalidation": "Stress or high realised vol on either scale.",
        "horizon": "10 bars",
    },
    AssetClass.MEME: {
        "hypothesis": "Qualified bursts need volume consistency, adaptive extension, RSI not extreme, and not pure Bollinger extreme.",
        "entry": "15% burst, vol consistency, extension adaptive, RSI ok, rising closes.",
        "invalidation": "Thin liquidity, excessive extension, overbought, or extreme channel without support.",
        "horizon": "3 bars",
    },
    AssetClass.L2: {
        "hypothesis": "Multi-period relative strength vs consistent non-stress benchmark with relative volume.",
        "entry": "Excess returns on 6/12 bars above adaptive, relative volume, benchmark consistent.",
        "invalidation": "Missing, stressed, or inconsistent benchmark.",
        "horizon": "12 bars",
    },
    AssetClass.RWA: {
        "hypothesis": "Slow multi-scale low-vol trend preferred; adaptive gap and stress halt.",
        "entry": "Close above EMA and prior, gap adaptive, positive slow momentum, low/normal vol.",
        "invalidation": "Gap, stress, or high vol.",
        "horizon": "24 bars",
    },
    AssetClass.PERPETUAL: {
        "hypothesis": "Negative funding with contained multi-bar drift, stability, consistency, non-stress.",
        "entry": "Funding <= -5 bps, |drift| adaptive, stable funding, consistency, not stress.",
        "invalidation": "Crowded funding, large drift, inconsistency, or stress.",
        "horizon": "8 bars",
    },
}


def _returns(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]


def _ema(values: list[float], span: int) -> float:
    alpha = 2.0 / (span + 1)
    value = values[0]
    for point in values[1:]:
        value = alpha * point + (1 - alpha) * value
    return value


def _macd_proxy(closes: list[float]) -> float:
    if len(closes) < 26:
        return 0.0
    return _ema(closes, 12) - _ema(closes, 26)


def _bollinger(closes: list[float], span: int = 20, mult: float = 2.0) -> tuple[float, float, float]:
    """Simple Bollinger: mid (SMA), upper, lower. Research proxy."""
    if len(closes) < span:
        mid = fmean(closes)
        return mid, mid, mid
    window = closes[-span:]
    mid = fmean(window)
    std = pstdev(window) if len(window) > 1 else 0.0
    return mid, mid + mult * std, mid - mult * std


def _adx_proxy(candles: list[Candle], period: int = 14) -> float:
    """Simple trend strength proxy from directional moves. 0-100 scale research."""
    if len(candles) < period + 1:
        return 20.0
    up_moves = []
    down_moves = []
    for i in range(1, min(period + 1, len(candles))):
        high_diff = candles[-i].high - candles[-i-1].high
        low_diff = candles[-i-1].low - candles[-i].low
        up_moves.append(max(high_diff, 0.0))
        down_moves.append(max(low_diff, 0.0))
    plus = fmean(up_moves) if up_moves else 0.0
    minus = fmean(down_moves) if down_moves else 0.0
    if plus + minus == 0:
        return 20.0
    return min(100.0, 100.0 * abs(plus - minus) / (plus + minus))


def _rsi(closes: list[float], period: int = 14) -> float:
    changes = _returns(closes[-(period + 1) :])
    gains = [max(change, 0.0) for change in changes]
    losses = [abs(min(change, 0.0)) for change in changes]
    average_loss = fmean(losses) if losses else 0.0
    if average_loss == 0:
        return 100.0
    rs = fmean(gains) / average_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr_pct(candles: list[Candle]) -> float:
    ranges = [(c.high - c.low) / c.close for c in candles[-14:] if c.close]
    return fmean(ranges) if ranges else 0.0


def _base(candles: list[Candle], side: Side, confidence: float, reason: str, size: float, bars: int) -> Signal:
    last = candles[-1]
    regime = classify(candles)
    vol = volatility_tier(candles)
    adj_conf = confidence * 0.90 if vol is VolatilityTier.HIGH else confidence
    return Signal(
        symbol=last.symbol,
        asset_class=last.asset_class,
        side=side,
        confidence=round(max(0.0, min(adj_conf, 1.0)), 4),
        reason=f"{reason}; regime={regime.value}; vol={vol.value}",
        stop_distance_pct=round(max(_atr_pct(candles) * 1.5, 0.01), 4),
        size_fraction=size,
        horizon_bars=bars,
    )


def signal_for(candles: list[Candle], benchmark: list[Candle] | None = None) -> Signal:
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    asset_class = candles[-1].asset_class
    closes = [c.close for c in candles]
    regime = classify(candles)
    vol = volatility_tier(candles)
    if asset_class is AssetClass.MAJOR:
        return _major(candles, closes, regime, vol)
    if asset_class is AssetClass.LARGE_CAP_ALT:
        return _breakout(candles, closes, size=0.04, bars=12, regime=regime, vol=vol)
    if asset_class is AssetClass.STABLECOIN:
        return _stable(candles, vol)
    if asset_class is AssetClass.DEFI:
        return _defi(candles, closes, regime, vol)
    if asset_class is AssetClass.MEME:
        return _meme(candles, closes, vol)
    if asset_class is AssetClass.L2:
        return _l2(candles, closes, benchmark, vol)
    if asset_class is AssetClass.RWA:
        return _rwa(candles, closes, regime, vol)
    return _perpetual(candles, closes, vol)


def _major(candles: list[Candle], closes: list[float], regime: Regime, vol: VolatilityTier) -> Signal:
    fast, mid, slow = _ema(closes, 5), _ema(closes, 8), _ema(closes, 13)
    rsi_period = 16 if vol is VolatilityTier.LOW else 12 if vol is VolatilityTier.HIGH else 14
    rsi = _rsi(closes, rsi_period)
    rsi_upper = 62 if vol is VolatilityTier.HIGH else 70
    rsi_lower_rev = 25 if vol is VolatilityTier.HIGH else 32
    macd = _macd_proxy(closes)
    macd_rising = macd > 0 and (len(closes) < 2 or macd > _macd_proxy(closes[:-1]))
    bb_mid, bb_upper, _ = _bollinger(closes)
    adx = _adx_proxy(candles)
    if regime is Regime.STRESS or (vol is VolatilityTier.HIGH and adx < 25):
        return _base(candles, Side.FLAT, 0.42, "major stress or high-vol weak trend: stand aside", 0.0, 1)
    if fast > mid > slow and macd_rising and closes[-1] >= bb_mid * 0.995 and adx > 22 and 45 <= rsi <= rsi_upper:
        return _base(candles, Side.LONG, 0.84, "major multi-EMA + MACD + Bollinger + ADX confirmation, adaptive RSI", 0.06, 20)
    if regime is Regime.RANGE and rsi < rsi_lower_rev and closes[-1] > closes[-3]:
        return _base(candles, Side.LONG, 0.68, "major mean-reversion: washed-out adaptive RSI in range", 0.03, 8)
    return _base(candles, Side.FLAT, 0.38, "major: no aligned multi-factor edge", 0.0, 1)


def _breakout(candles: list[Candle], closes: list[float], size: float, bars: int, regime: Regime, vol: VolatilityTier) -> Signal:
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.38, "breakout suppressed in stress", 0.0, 1)
    window = closes[-6:-1]
    volume_now = candles[-1].volume
    volume_base = fmean(c.volume for c in candles[-6:-1])
    mom_short = closes[-1] / closes[-3] - 1.0
    mom_med = closes[-1] / closes[-6] - 1.0
    vol_mult = 1.7 if vol is VolatilityTier.HIGH else 1.35
    macd = _macd_proxy(closes)
    _, bb_upper, _ = _bollinger(closes, 15)
    if closes[-1] > max(window) and closes[-1] > bb_upper * 0.998 and volume_now > volume_base * vol_mult and mom_short > 0.007 and mom_med > 0.0 and macd > 0:
        return _base(candles, Side.LONG, 0.79, "volume-confirmed breakout with multi-momentum, MACD, Bollinger", size, bars)
    return _base(candles, Side.FLAT, 0.33, "no confirmed multi-factor breakout", 0.0, 1)


def _stable(candles: list[Candle], vol: VolatilityTier) -> Signal:
    deviation = abs(candles[-1].close - 1.0)
    closes = [c.close for c in candles[-20:]]
    z = 0.0
    if len(closes) > 5:
        mean_p = fmean(closes)
        std_p = pstdev(closes) if len(closes) > 1 else 0.001
        z = abs(candles[-1].close - mean_p) / max(std_p, 0.001)
    watch = 0.0025 if vol is VolatilityTier.HIGH else 0.002
    depeg = 0.006 if vol is VolatilityTier.HIGH else 0.005
    if deviation >= depeg or z > 3.5:
        return _base(candles, Side.ALERT, 0.94, f"stablecoin depeg monitor: deviation {deviation:.4f} z={z:.2f}", 0.0, 1)
    if deviation >= watch or z > 2.2:
        return _base(candles, Side.ALERT, 0.74, f"stablecoin watch band: deviation {deviation:.4f} z={z:.2f}", 0.0, 1)
    return _base(candles, Side.FLAT, 0.81, "stablecoin inside peg band", 0.0, 1)


def _defi(candles: list[Candle], closes: list[float], regime: Regime, vol: VolatilityTier) -> Signal:
    realised = fmean(abs(v) for v in _returns(closes[-8:]))
    vol_limit = 0.045 if vol is VolatilityTier.HIGH else 0.058
    mom = closes[-1] / closes[-5] - 1.0
    bb_mid, _, _ = _bollinger(closes, 10)
    if regime is Regime.STRESS or realised > vol_limit:
        return _base(candles, Side.FLAT, 0.46, "defi volatility regime: stand aside", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and closes[-1] > bb_mid and mom > 0.004:
        return _base(candles, Side.LONG, 0.74, "defi trend in calm multi-scale regime with channel and momentum", 0.02, 10)
    return _base(candles, Side.FLAT, 0.39, "defi: no calm multi-factor trend", 0.0, 1)


def _meme(candles: list[Candle], closes: list[float], vol: VolatilityTier) -> Signal:
    liquidity = fmean(c.volume for c in candles[-5:])
    burst = closes[-1] / closes[-4] - 1.0
    extension = closes[-1] / closes[-8] - 1.0
    vol_accel = candles[-1].volume / max(candles[-2].volume, 1)
    rising = closes[-1] > closes[-2] > closes[-3]
    rsi = _rsi(closes)
    ext_limit = 0.26 if vol is VolatilityTier.HIGH else 0.33
    accel_req = 1.4 if vol is VolatilityTier.HIGH else 1.25
    _, bb_upper, _ = _bollinger(closes, 10)
    if liquidity < 1000:
        return _base(candles, Side.FLAT, 0.18, "meme liquidity proxy too thin", 0.0, 1)
    if extension > ext_limit or rsi > 76 or closes[-1] > bb_upper * 1.05:
        return _base(candles, Side.FLAT, 0.33, "meme chase filter: extension, RSI, or extreme Bollinger", 0.0, 1)
    if burst > 0.15 and vol_accel > accel_req and rising:
        return _base(candles, Side.LONG, 0.85, "meme momentum burst with volume consistency, RSI ok; hard time stop", 0.005, 3)
    return _base(candles, Side.FLAT, 0.28, "meme: no qualified multi-factor burst", 0.0, 1)


def _l2(candles: list[Candle], closes: list[float], benchmark: list[Candle] | None, vol: VolatilityTier) -> Signal:
    if not benchmark or len(benchmark) < 12:
        return _base(candles, Side.FLAT, 0.28, "l2 requires a benchmark series", 0.0, 1)
    if classify(benchmark) is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.40, "l2 benchmark in stress", 0.0, 1)
    own6 = closes[-1] / closes[-6] - 1.0
    own12 = closes[-1] / closes[-12] - 1.0
    bench_closes = [c.close for c in benchmark]
    bench6 = bench_closes[-1] / bench_closes[-6] - 1.0
    bench12 = bench_closes[-1] / bench_closes[-12] - 1.0
    thresh6 = 0.036 if vol is VolatilityTier.HIGH else 0.029
    thresh12 = 0.026 if vol is VolatilityTier.HIGH else 0.019
    own_vol = fmean(c.volume for c in candles[-6:])
    bench_vol = fmean(c.volume for c in benchmark[-6:]) if benchmark else 1
    rel_vol = own_vol / max(bench_vol, 1)
    if own6 - bench6 > thresh6 and own12 - bench12 > thresh12 and rel_vol > 0.85:
        return _base(candles, Side.LONG, 0.77, "l2 multi-period relative strength + relative volume versus consistent benchmark", 0.03, 12)
    return _base(candles, Side.FLAT, 0.38, "l2 not leading benchmark on multi-period with volume", 0.0, 1)


def _rwa(candles: list[Candle], closes: list[float], regime: Regime, vol: VolatilityTier) -> Signal:
    gap = candles[-1].open / candles[-2].close - 1.0
    gap_limit = 0.06 if vol is VolatilityTier.HIGH else 0.075
    mom = closes[-1] / closes[-8] - 1.0
    if abs(gap) > gap_limit or regime is Regime.STRESS or vol is VolatilityTier.HIGH:
        return _base(candles, Side.FLAT, 0.48, "rwa gap, stress, or high vol halt", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and closes[-1] > closes[-5] and mom > 0.0:
        return _base(candles, Side.LONG, 0.72, "rwa slow multi-scale trend with positive momentum", 0.02, 24)
    return _base(candles, Side.FLAT, 0.38, "rwa: no slow multi-scale trend with momentum", 0.0, 1)


def _perpetual(candles: list[Candle], closes: list[float], vol: VolatilityTier) -> Signal:
    funding = candles[-1].funding_rate
    prev_funding = candles[-2].funding_rate if len(candles) > 1 else funding
    drift = closes[-1] / closes[-6] - 1.0
    funding_stable = abs(funding - prev_funding) < 0.0002
    drift_limit = 0.03 if vol is VolatilityTier.HIGH else 0.038
    mom = closes[-1] / closes[-3] - 1.0
    consistency = abs(closes[-1] / closes[-4] - 1.0) < 0.025
    if funding >= 0.001:
        return _base(candles, Side.ALERT, 0.73, "perp funding crowded: monitor, no carry", 0.0, 1)
    if funding <= -0.0005 and abs(drift) < drift_limit and funding_stable and abs(mom) < 0.028 and consistency:
        return _base(candles, Side.LONG, 0.80, "perp funding carry: negative funding, multi-bar drift contained, stable, consistent", 0.02, 8)
    if funding <= -0.0005:
        return _base(candles, Side.FLAT, 0.48, "perp funding attractive but drift, stability, or consistency not met", 0.0, 1)
    return _base(candles, Side.FLAT, 0.38, "perp: no carry edge", 0.0, 1)
