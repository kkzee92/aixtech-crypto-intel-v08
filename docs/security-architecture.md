# Security architecture (v0.8 enhanced)

Version 0.8 expands the research control plane with statistical anomaly scoring (z-score style), additional secret patterns (private key formats, more API variants, JWT fragments), fixture integrity checksums, multi-scale consistency checks, and refined zero-trust principles. Research design only; not a certified product, not legal or compliance advice.

## Trust boundaries

```mermaid
flowchart LR
    F[\"Synthetic fixture or injected public ticker\"] --> AT[\"Source attestation + checksum + statistical multi-bar anomaly + consistency\"]
    AT --> S[\"Strategy rules + multi-scale regime + Bollinger/ADX proxies + adaptive vol\"]
    S --> R[\"Risk gate: class caps, kill switch, drawdown, adaptive size/confidence\"]
    R --> P[\"Paper fill only\"]
    P --> A[\"Hash-chained audit with enhanced sanitization, integrity tags, anomaly notes\"]
    K[\"Trade or withdrawal keys\"] -.-> X[\"Refused. Never loaded\"]
    RBAC[\"Researcher, auditor, operator\"] --> R
```

No order router. `assert_paper_only` enforces PAPER only. Zero-trust: every input attested and scored; logs sanitized.

## Roles

| Role | Allowed | Denied |
|---|---|---|
| Researcher | scan, backtest, read audit, anomaly review | place order, withdraw, enable live |
| Auditor | read audit, verify chain, scan, integrity checks | place order, withdraw, enable live |
| Operator | scan, kill switch, read audit | place order, withdraw, enable live |

No trader role. Broker promotion is separate and human-approved.

## Data classes

| Field | Class | Handling | Protection |
|---|---|---|---|
| Symbol, OHLCV | Public market | Synthetic | Research retention |
| Funding | Public | Research only | Research |
| Source label | Integrity | SYNTHETIC or PUBLIC_READ + checksum | Attested |
| Read-only market key | Secret optional | Name-restricted, never logged | External rotate |
| Trade/withdrawal key | Secret | Refused | Never stored |
| Wallet | Sensitive identifier | Redacted, banned | Do not collect |
| Email/NRIC/phone | Personal | Tripwire + redaction | Do not collect |

## Feed integrity and anomaly

`anomaly_score` now includes z-score style deviations on returns and volume, consecutive anomalies, multi-bar consistency, and staleness. High scores are research notes only. `sanitize_input` redacts expanded patterns (private keys, AWS, Slack, JWT fragments, hex, base64-like), wallets, phones; length-limits and strips controls. Source attestation includes version tag and body hash. Loader rejects non-SYNTHETIC.

## Threats and controls

| Threat | Control |
|---|---|
| Secret committed | gitleaks CI, expanded redaction (private keys, JWT, AWS, Slack, API variants), no loader |
| Trade key pasted | refuse_trade_secret |
| Fixture injection | SYNTHETIC + checksum + attestation + statistical anomaly |
| Stale/jumped data | multi-bar z-score anomaly + consistency |
| Oversized risk | class caps, adaptive floors, vol/stress size reduction |
| Runaway loss | drawdown halt + kill switch |
| Audit tamper | SHA-256 chain + integrity tags; verify |
| Live mistake | mode guard, no client, RBAC deny, paper-only |
| Personal data | tripwire + redaction |
| Privilege creep | no order-capable role |
| Input injection | sanitization + length limits |
| Replay | timestamps + consecutive scoring |

## Incident handling

1. Kill switch to zero new size.
2. Freeze audit; record attestation, checksum, high anomaly scores.
3. Rotate any secret externally; purge history; review CI.
4. No public issues with secrets, wallets, or personal data.
5. Human review required before clearing kill switch.
6. Update patterns and thresholds post-incident.

## Operating rules

- Credentials (if ever) read-only, separate, never logged.
- All logs through sanitize/redact.
- Default research/paper-only. Broker is separate.
- Zero-trust: attest, score, verify chain, assume adversarial inputs.
- Future stores: AES-256 + TLS. Synthetic only here.
- Monitor anomalies, kill activations, attestation failures.
- Secrets managed externally.
- Audit is research-level; production needs append-only + anchoring.
- Strategies and gates versioned with human review and tests.
- Adaptive risk reduces exposure in high-vol or inconsistent regimes.

Prioritizes research integrity, transparency of heuristics, and prevention of accidental live execution or leakage.
