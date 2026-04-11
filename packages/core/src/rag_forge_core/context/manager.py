"""Context window management and enrichment."""

from dataclasses import dataclass


@dataclass
class ContextWindow:
    """Tracks context window utilization per LLM call."""

    max_tokens: int
    used_tokens: int = 0
    chunks_included: int = 0

    @property
    def utilization(self) -> float:
        """Context window utilization as a percentage."""
        if self.max_tokens == 0:
            return 0.0
        return self.used_tokens / self.max_tokens

    @property
    def is_near_limit(self) -> bool:
        """True if context usage exceeds 80% of model limit."""
        return self.utilization > 0.8


class ContextManager:
    """Manages context window tracking and chunk enrichment.

    Handles context rot prevention by tracking window utilization
    and applying enrichment techniques to maintain chunk quality.
    """

    def __init__(self, max_tokens: int = 128_000) -> None:
        self.max_tokens = max_tokens
        self._window = ContextWindow(max_tokens=max_tokens)

    @property
    def window(self) -> ContextWindow:
        """Current context window state."""
        return self._window

    def reset(self) -> None:
        """Reset the context window for a new query."""
        self._window = ContextWindow(max_tokens=self.max_tokens)
