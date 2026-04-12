"""PII scanning: Presidio (optional) with regex fallback."""

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class PIIDetection:
    """A single PII detection result."""

    entity_type: str
    text: str
    start: int
    end: int
    score: float


@dataclass
class PIIScanResult:
    """Result of a PII scan."""

    has_pii: bool
    detections: list[PIIDetection] = field(default_factory=list)


@runtime_checkable
class PIIScannerProtocol(Protocol):
    """Protocol for PII scanning implementations."""

    def scan(self, text: str) -> PIIScanResult: ...


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("PHONE_NUMBER", re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")),
    ("IP_ADDRESS", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
]


class RegexPIIScanner:
    """Lightweight PII scanner using regex patterns."""

    def scan(self, text: str) -> PIIScanResult:
        """Scan text for PII using regex patterns."""
        detections: list[PIIDetection] = []
        for entity_type, pattern in _PATTERNS:
            for match in pattern.finditer(text):
                detections.append(
                    PIIDetection(
                        entity_type=entity_type,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        score=0.8,
                    )
                )
        return PIIScanResult(has_pii=len(detections) > 0, detections=detections)


class PresidioPIIScanner:
    """Full PII scanner using Microsoft Presidio.

    Requires: pip install rag-forge-core[presidio]
    """

    def __init__(self, language: str = "en") -> None:
        from presidio_analyzer import AnalyzerEngine

        self._analyzer = AnalyzerEngine()
        self._language = language

    def scan(self, text: str) -> PIIScanResult:
        """Scan text for PII using Presidio."""
        results = self._analyzer.analyze(text=text, language=self._language)
        detections = [
            PIIDetection(
                entity_type=r.entity_type,
                text=text[r.start : r.end],
                start=r.start,
                end=r.end,
                score=r.score,
            )
            for r in results
        ]
        return PIIScanResult(has_pii=len(detections) > 0, detections=detections)
