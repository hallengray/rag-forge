"""Rate limiting with pluggable storage backend."""

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class RateLimitStore(Protocol):
    """Protocol for rate limit state storage."""

    def record(self, user_id: str) -> None: ...
    def count(self, user_id: str, window_seconds: int) -> int: ...


class InMemoryRateLimitStore:
    """In-memory sliding window rate limit store."""

    def __init__(self) -> None:
        self._entries: dict[str, list[float]] = {}

    def record(self, user_id: str) -> None:
        if user_id not in self._entries:
            self._entries[user_id] = []
        self._entries[user_id].append(time.monotonic())

    def count(self, user_id: str, window_seconds: int) -> int:
        if user_id not in self._entries:
            return 0
        cutoff = time.monotonic() - window_seconds
        self._entries[user_id] = [ts for ts in self._entries[user_id] if ts > cutoff]
        return len(self._entries[user_id])

    def check_and_record(self, user_id: str, window_seconds: int, max_queries: int) -> int:
        """Atomically check count and record if under limit. Returns current count after operation."""
        if user_id not in self._entries:
            self._entries[user_id] = []
        cutoff = time.monotonic() - window_seconds
        self._entries[user_id] = [ts for ts in self._entries[user_id] if ts > cutoff]
        current = len(self._entries[user_id])
        if current < max_queries:
            self._entries[user_id].append(time.monotonic())
        return current


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    current_count: int
    limit: int
    window_seconds: int


class RateLimiter:
    """Rate limiter with configurable limits and pluggable storage."""

    def __init__(
        self,
        max_queries: int = 60,
        window_seconds: int = 60,
        store: RateLimitStore | None = None,
    ) -> None:
        self._max_queries = max_queries
        self._window_seconds = window_seconds
        self._store = store or InMemoryRateLimitStore()

    def check(self, user_id: str = "default") -> RateLimitResult:
        """Check rate limit for user. Records the query if allowed."""
        if isinstance(self._store, InMemoryRateLimitStore):
            current = self._store.check_and_record(user_id, self._window_seconds, self._max_queries)
            return RateLimitResult(
                allowed=current < self._max_queries,
                current_count=min(current + 1, self._max_queries) if current < self._max_queries else current,
                limit=self._max_queries,
                window_seconds=self._window_seconds,
            )
        # Fallback for custom stores
        current = self._store.count(user_id, self._window_seconds)
        if current >= self._max_queries:
            return RateLimitResult(
                allowed=False,
                current_count=current,
                limit=self._max_queries,
                window_seconds=self._window_seconds,
            )
        self._store.record(user_id)
        return RateLimitResult(
            allowed=True,
            current_count=current + 1,
            limit=self._max_queries,
            window_seconds=self._window_seconds,
        )
