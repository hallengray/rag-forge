"""Post-generation security pipeline.

Checks for faithfulness, PII leakage, citation validity, and staleness.
"""

from dataclasses import dataclass


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
    """Post-generation security interceptor chain.

    Runs after LLM generation to verify:
    - Response faithfulness to retrieved context
    - No PII leakage in output
    - All citations map to valid chunk IDs
    - Context freshness (staleness detection)
    """

    def __init__(self, faithfulness_threshold: float = 0.85) -> None:
        self.faithfulness_threshold = faithfulness_threshold

    def check(self, response: str, contexts: list[str]) -> OutputGuardResult:
        """Run all output guards on a generated response."""
        # Stub: full implementation in Phase 2 (security module)
        _ = response, contexts
        return OutputGuardResult(passed=True)
