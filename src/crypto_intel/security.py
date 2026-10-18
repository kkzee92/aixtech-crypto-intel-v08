"""Cyber and data-security controls for the information system (v0.8).

Research control plane with expanded redaction, statistical anomaly scoring, and integrity notes. Not a certified security product.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from statistics import fmean, pstdev

from crypto_intel.models import AuditEvent, ExecutionMode

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token|private[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-\/+=]{12,}"),
    re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS-style
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),  # Slack
    re.compile(r"\b[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),  # JWT-like fragments
    re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:0x)?[a-fA-F0-9]{64}\b"),  # hex private-key-like
)

WALLET_PATTERN = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
PHONE_PATTERN = re.compile(r"\b\+?[0-9][0-9\-\s]{8,}\b")


@dataclass(frozen=True)
class DataClassification:
    field: str
    level: str
    retention: str


CLASSIFICATION = (
    DataClassification("symbol", "public", "research retention"),
    DataClassification("ohlcv", "public-market", "research retention"),
    DataClassification("exchange_api_key", "secret", "never stored"),
    DataClassification("wallet_address", "sensitive-identifier", "do not fixture"),
    DataClassification("account_email", "personal", "do not collect"),
)


def redact(text: str) -> str:
    cleaned = text
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    cleaned = WALLET_PATTERN.sub("[WALLET]", cleaned)
    cleaned = PHONE_PATTERN.sub("[PHONE]", cleaned)
    return cleaned


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS) or bool(WALLET_PATTERN.search(text))


def assert_paper_only(mode: ExecutionMode) -> None:
    if mode is not ExecutionMode.PAPER:
        raise PermissionError("live execution is disabled; this system is paper-only")


def hash_event(previous_hash: str, sequence: int, action: str, detail: str) -> str:
    material = f"{previous_hash}|{sequence}|{action}|{detail}".encode()
    return hashlib.sha256(material).hexdigest()


def anomaly_score(closes: list[float], volumes: list[float] | None = None) -> float:
    """Statistical research anomaly score 0-1 using z-style deviations."""
    if len(closes) < 5:
        return 0.0
    rets = [closes[i] / closes[i-1] - 1.0 for i in range(1, len(closes))]
    mean_r = fmean(rets)
    std_r = pstdev(rets) if len(rets) > 1 else 0.01
    z_r = abs(rets[-1] - mean_r) / max(std_r, 0.001) if rets else 0.0
    score = min(1.0, z_r / 4.0)
    if volumes and len(volumes) >= 5:
        mean_v = fmean(volumes)
        std_v = pstdev(volumes) if len(volumes) > 1 else 1.0
        z_v = abs(volumes[-1] - mean_v) / max(std_v, 1.0)
        score = min(1.0, max(score, z_v / 5.0))
    # consecutive jump penalty
    if len(rets) >= 2 and abs(rets[-1]) > 0.05 and abs(rets[-2]) > 0.04:
        score = min(1.0, score + 0.15)
    return round(score, 3)


class AuditLog:
    """Append-only hash chain with integrity notes. Tampering changes the next digest."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._previous = "GENESIS"

    def append(self, action: str, detail: str, anomaly: float = 0.0) -> AuditEvent:
        safe_detail = redact(detail)
        if anomaly > 0.6:
            safe_detail += f" | anomaly={anomaly}"
        sequence = len(self.events) + 1
        digest = hash_event(self._previous, sequence, action, safe_detail)
        event = AuditEvent(sequence, action, safe_detail, self._previous, digest)
        self.events.append(event)
        self._previous = digest
        return event

    def verify(self) -> bool:
        previous = "GENESIS"
        for event in self.events:
            expected = hash_event(previous, event.sequence, event.action, event.detail)
            if event.previous_hash != previous or event.digest != expected:
                return False
            previous = event.digest
        return True


def fixture_checksum(label: str, body: str) -> str:
    """Research integrity checksum for fixtures."""
    material = f"v0.8|{label}|{body}".encode()
    return hashlib.sha256(material).hexdigest()[:16]
