"""PII scanner for vector store collections.

Scans all chunks in a collection for PII using RegexPIIScanner.
Reports affected chunk IDs and PII type counts.
"""

from dataclasses import dataclass, field
from typing import Any

from rag_forge_core.security.pii import RegexPIIScanner


@dataclass
class PIIScanReport:
    """Result of scanning a collection for PII."""

    chunks_scanned: int
    chunks_with_pii: int
    pii_types: dict[str, int]
    affected_chunks: list[str] = field(default_factory=list)


class PIICollectionScanner:
    """Scans a list of chunks for PII leakage."""

    def __init__(self) -> None:
        self._scanner = RegexPIIScanner()

    def scan_chunks(self, chunks: list[dict[str, Any]]) -> PIIScanReport:
        """Scan chunks for PII. Each chunk must have 'id' and 'text' keys."""
        pii_types: dict[str, int] = {}
        affected: list[str] = []

        for chunk in chunks:
            result = self._scanner.scan(chunk["text"])
            if result.has_pii:
                affected.append(chunk["id"])
                for detection in result.detections:
                    pii_types[detection.entity_type] = pii_types.get(detection.entity_type, 0) + 1

        return PIIScanReport(
            chunks_scanned=len(chunks),
            chunks_with_pii=len(affected),
            pii_types=pii_types,
            affected_chunks=affected,
        )
