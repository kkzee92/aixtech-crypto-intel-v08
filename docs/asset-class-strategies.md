# Asset-class strategy notes (v0.8)

Research heuristics with multi-factor confirmation, multi-scale regimes, Bollinger-style channels, and ADX-like trend strength. Not forecasts. Version 0.8 adds volatility channels, trend strength proxies, and tighter adaptive filters.

Multi-scale regime from `regime.py` (short 8-bar and medium 20-bar lookbacks):

- **trend**: consistent directional move above threshold on both scales, bar range under stress band
- **range**: neither stress nor clear trend on scales
- **stress**: elevated average bar range or large single-bar moves; directional ideas stand aside

Volatility tiers remain low/normal/high.

## Major

Hypothesis: liquid majors show reliable multi-EMA alignment with MACD and Bollinger confirmation plus trend strength when not in stress or mismatched high vol. Mean reversion only in confirmed range with washed-out adaptive RSI. Cap 8%. Horizon 8/20 bars. Cost 8 bps.

## Large-cap alt

Hypothesis: breakouts need volume, multi-momentum, MACD, and Bollinger upper channel breach outside stress. Cap 4%. Cost 14 bps.

## Stablecoin

Hypothesis: useful signal is statistical peg deviation. Adaptive + z-score style watch/depeg alerts. No order. Cap 0%.

## DeFi

Hypothesis: trend only in multi-scale calm non-stress with momentum and channel support. Cap 2%. Cost 22 bps.

## Meme

Hypothesis: most bursts untradeable. Qualified require volume consistency, adaptive extension limits, RSI not extreme, and not at Bollinger extreme without confirmation. Cap 0.5%. Cost 45 bps. Hard 3-bar horizon.

## L2

Hypothesis: multi-period relative strength vs non-stress, consistent benchmark, with relative volume. Cap 3%. Cost 16 bps.

## RWA

Hypothesis: slow assets prefer multi-scale low-vol trends; adaptive gap and stress halt. Cap 2%. Horizon 24 bars. Cost 12 bps.

## Perpetual

Hypothesis: negative funding carry with contained multi-bar drift, funding stability, consistency, non-stress. Crowded funding is alert only. Cap 2%. Cost 10 bps. Does not model liquidation or exchange risk.

## Still out of scope

- Live order routing or any trade/withdrawal keys.
- Broker adapters (separate human-approved system).
- Claims of future returns. Scores are on synthetic data only.
