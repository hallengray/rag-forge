"""Pre-retrieval security pipeline.

Composes individual input checks into a chain.
Runs checks in order, stops at the first failure.
"""

from dataclasses import dataclass

from rag_forge_core.security.injection import (
    PromptInjectionClassifier,
    PromptInjectionDetector,
)
from rag_forge_core.security.pii import PIIScannerProtocol
from rag_forge_core.security.rate_limiter import RateLimiter


@dataclass
class GuardResult:
    """Result of a security guard check."""

    passed: bool
    reason: str | None = None
    blocked_by: str | None = None


class InputGuard:
    """Pre-retrieval security interceptor chain."""

    def __init__(
        self,
        injection_detector: PromptInjectionDetector | None = None,
        injection_classifier: PromptInjectionClassifier | None = None,
        pii_scanner: PIIScannerProtocol | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._injection_detector = injection_detector
        self._injection_classifier = injection_classifier
        self._pii_scanner = pii_scanner
        self._rate_limiter = rate_limiter

    def check(self, query: str, user_id: str = "default") -> GuardResult:
        """Run all configured input checks in order.

        Check order: rate limiter -> injection detector -> injection classifier -> PII scanner.
        Rate limiting runs first to prevent abusive callers from spamming blocked payloads
        without consuming quota.
        """
        if self._rate_limiter is not None:
            rate_result = self._rate_limiter.check(user_id)
            if not rate_result.allowed:
                return GuardResult(
                    passed=False,
                    reason=f"Rate limit exceeded: {rate_result.current_count}/{rate_result.limit} queries in {rate_result.window_seconds}s",
                    blocked_by="rate_limiter",
                )

        if self._injection_detector is not None:
            result = self._injection_detector.check(query)
            if result.is_injection:
                return GuardResult(
                    passed=False,
                    reason=f"Prompt injection detected: {result.pattern_matched}",
                    blocked_by="prompt_injection_detector",
                )

        if self._injection_classifier is not None:
            result = self._injection_classifier.check(query)
            if result.is_injection:
                return GuardResult(
                    passed=False,
                    reason=f"Prompt injection classified: {result.pattern_matched}",
                    blocked_by="prompt_injection_classifier",
                )

        if self._pii_scanner is not None:
            scan_result = self._pii_scanner.scan(query)
            if scan_result.has_pii:
                entity_types = ", ".join(d.entity_type for d in scan_result.detections)
                return GuardResult(
                    passed=False,
                    reason=f"PII detected in query: {entity_types}",
                    blocked_by="pii_scanner",
                )

        return GuardResult(passed=True)
