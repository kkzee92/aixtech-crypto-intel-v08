# AIxTech crypto intel v0.8: paper-only trading information system

Further enhanced research harness for automated cryptocurrency **information** and paper strategy evaluation.
Builds on [kkzee92/aixtech-crypto-intel-enhanced](https://github.com/kkzee92/aixtech-crypto-intel-enhanced) (v0.7) and original [zeekiankok92/aixtech-crypto-intel](https://github.com/zeekiankok92/aixtech-crypto-intel).

It does not place live orders, does not store exchange secrets, and is not financial advice.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![version](https://img.shields.io/badge/version-0.8.0-blue)
![mode](https://img.shields.io/badge/execution-paper%20only-orange)
![Licence](https://img.shields.io/badge/licence-MIT-green)

## Enhancements in v0.8

- Bollinger-style volatility channels and ADX-like trend strength proxies for majors and large-caps.
- Multi-scale regime detection (short and medium lookbacks) with consistency scoring.
- Adaptive volume and momentum filters refined; relative strength improved for L2 and RWA.
- Expanded secret redaction (private key formats, additional API variants, JWT fragments).
- Statistical anomaly scoring (z-score style on returns and volume) + multi-bar consistency.
- Additional data integrity: fixture checksums and source attestation with version tags.
- Stronger zero-trust controls documented; adaptive risk further tightened in high-vol/stress.

See [docs/asset-class-strategies.md](docs/asset-class-strategies.md) and [docs/security-architecture.md](docs/security-architecture.md).

## What it does

- Classifies into eight asset classes with advanced research rules per class.
- Multi-scale regime (trend/range/stress) + volatility tiers.
- Multi-factor signals (EMA alignment, MACD, Bollinger, ADX proxy, volume, adaptive RSI) then risk gate.
- Paper backtests with class costs; hash-chained audit with enhanced sanitization and anomaly notes.
- Synthetic candles only. No network by default.

| Asset class | Enhanced research rule (v0.8) | Risk cap (base) | Cost |
|---|---|---|---|
| Major | Multi-EMA + MACD + Bollinger channel + ADX proxy, adaptive RSI, stand aside in stress/high-vol mismatch | 8% | 8 bps |
| Large-cap alt | Volume + multi-momentum + MACD + Bollinger breakout confirmation | 4% | 14 bps |
| Stablecoin | Adaptive peg + statistical deviation alerts only | 0% | n/a |
| DeFi | Calm multi-scale regime trend + momentum + vol channel | 2% | 22 bps |
| Meme | Qualified burst with tighter adaptive filters, volume consistency, RSI, Bollinger extremes | 0.5% | 45 bps |
| L2 | Multi-period relative strength + relative volume + benchmark regime consistency | 3% | 16 bps |
| RWA | Slow multi-scale trend, adaptive gap, momentum, low-vol preference | 2% | 12 bps |
| Perpetual | Funding carry with adaptive drift, funding stability, multi-bar consistency, non-stress | 2% | 10 bps |

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/make_fixtures.py
PYTHONPATH=src python -m crypto_intel scan fixtures/candles_synthetic.json
PYTHONPATH=src python -m crypto_intel brief fixtures/candles_synthetic.json
PYTHONPATH=src python -m crypto_intel posture fixtures/candles_synthetic.json
```

## Controls

Paper-only execution. No live credentials. Class caps, multi-factor adaptive confidence floors, kill switch, drawdown halt, statistical + multi-bar anomaly detection, hash-chained audit with integrity tags, PDPA tripwire, gitleaks. Zero-trust research design.

## Honesty

No live exchange connector. Scores describe synthetic fixtures. Not investment, legal, or compliance advice. Research only.
