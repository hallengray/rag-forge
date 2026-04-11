"""Pre-retrieval security pipeline.

Checks for prompt injection, out-of-scope queries, rate limits, and PII.
"""

from dataclasses import dataclass


@dataclass
class GuardResult:
    """Result of a security guard check."""

    passed: bool
    reason: str | None = None
    blocked_by: str | None = None


class InputGuard:
    """Pre-retrieval security interceptor chain.

    Runs before any retrieval or LLM call to detect:
    - Prompt injection attempts
    - Out-of-scope queries
    - Rate limit violations
    - PII in user input
    """

    def check(self, query: str) -> GuardResult:
        """Run all input guards on a query."""
        # Stub: full implementation in Phase 2 (security module)
        _ = query
        return GuardResult(passed=True)
