"""Post-generation security pipeline.

Composes individual output checks into a chain.
Runs checks in order, stops at the first failure.
"""

import logging
from dataclasses import dataclass

from rag_forge_core.security.citations import CitationValidator
from rag_forge_core.security.faithfulness import FaithfulnessChecker
from rag_forge_core.security.pii import PIIScannerProtocol
from rag_forge_core.security.staleness import StalenessChecker

logger = logging.getLogger(__name__)


@dataclass
class OutputGuardResult:
    """Result of output security checks."""

    passed: bool
    faithfulness_score: float | None = None
    pii_detected: bool = False
    citations_valid: bool = True
    stale_context: bool = False
    reason: str | None = None


class OutputGuard:
    """Post-generation security interceptor chain."""

    def __init__(
        self,
        faithfulness_checker: FaithfulnessChecker | None = None,
        pii_scanner: PIIScannerProtocol | None = None,
        citation_validator: CitationValidator | None = None,
        staleness_checker: StalenessChecker | None = None,
    ) -> None:
        self._faithfulness_checker = faithfulness_checker
        self._pii_scanner = pii_scanner
        self._citation_validator = citation_validator
        self._staleness_checker = staleness_checker

    def check(
        self,
        response: str,
        contexts: list[str],
        chunk_ids: list[str] | None = None,
        contexts_metadata: list[dict[str, str | int | float]] | None = None,
    ) -> OutputGuardResult:
        """Run all configured output checks."""
        faithfulness_score: float | None = None

        if self._faithfulness_checker is not None:
            faith_result = self._faithfulness_checker.check(response, contexts)
            faithfulness_score = faith_result.score
            if not faith_result.passed:
                return OutputGuardResult(
                    passed=False,
                    faithfulness_score=faith_result.score,
                    reason=f"Faithfulness below threshold: {faith_result.score:.2f} < {faith_result.threshold}",
                )

        if self._pii_scanner is not None:
            scan_result = self._pii_scanner.scan(response)
            if scan_result.has_pii:
                entity_types = ", ".join(d.entity_type for d in scan_result.detections)
                return OutputGuardResult(
                    passed=False,
                    faithfulness_score=faithfulness_score,
                    pii_detected=True,
                    reason=f"PII detected in response: {entity_types}",
                )

        if self._citation_validator is not None:
            if chunk_ids is None:
                logger.warning("CitationValidator configured but chunk_ids not provided, skipping")
            else:
                cite_result = self._citation_validator.check(response, valid_source_count=len(chunk_ids))
                if not cite_result.passed:
                    return OutputGuardResult(
                        passed=False,
                        faithfulness_score=faithfulness_score,
                        citations_valid=False,
                        reason=f"Invalid citations: {', '.join(cite_result.invalid_citations)}",
                    )

        if self._staleness_checker is not None:
            if contexts_metadata is None:
                logger.warning("StalenessChecker configured but contexts_metadata not provided, skipping")
            else:
                stale_result = self._staleness_checker.check(contexts_metadata)
                if not stale_result.passed:
                    return OutputGuardResult(
                        passed=False,
                        faithfulness_score=faithfulness_score,
                        stale_context=True,
                        reason=f"Stale context: {', '.join(stale_result.stale_sources)}",
                    )

        return OutputGuardResult(passed=True, faithfulness_score=faithfulness_score)
