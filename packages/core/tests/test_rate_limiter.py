"""Tests for rate limiting."""

from rag_forge_core.security.rate_limiter import (
    InMemoryRateLimitStore,
    RateLimiter,
    RateLimitResult,
    RateLimitStore,
)


class TestInMemoryRateLimitStore:
    def test_implements_protocol(self) -> None:
        assert isinstance(InMemoryRateLimitStore(), RateLimitStore)

    def test_record_and_count(self) -> None:
        store = InMemoryRateLimitStore()
        store.record("user1")
        store.record("user1")
        store.record("user2")
        assert store.count("user1", window_seconds=60) == 2
        assert store.count("user2", window_seconds=60) == 1

    def test_count_empty_user(self) -> None:
        store = InMemoryRateLimitStore()
        assert store.count("unknown", window_seconds=60) == 0

    def test_expired_entries_not_counted(self) -> None:
        store = InMemoryRateLimitStore()
        store.record("user1")
        assert store.count("user1", window_seconds=60) == 1
        assert store.count("user1", window_seconds=0) == 0


class TestRateLimiter:
    def test_allows_within_limit(self) -> None:
        limiter = RateLimiter(max_queries=5, window_seconds=60)
        result = limiter.check("user1")
        assert result.allowed
        assert isinstance(result, RateLimitResult)

    def test_blocks_when_exceeded(self) -> None:
        limiter = RateLimiter(max_queries=3, window_seconds=60)
        limiter.check("user1")
        limiter.check("user1")
        limiter.check("user1")
        result = limiter.check("user1")
        assert not result.allowed
        assert result.current_count == 3
        assert result.limit == 3

    def test_different_users_independent(self) -> None:
        limiter = RateLimiter(max_queries=2, window_seconds=60)
        limiter.check("user1")
        limiter.check("user1")
        result_user2 = limiter.check("user2")
        assert result_user2.allowed

    def test_result_fields(self) -> None:
        limiter = RateLimiter(max_queries=10, window_seconds=30)
        result = limiter.check("user1")
        assert result.limit == 10
        assert result.window_seconds == 30
        assert result.current_count == 1

    def test_custom_store(self) -> None:
        store = InMemoryRateLimitStore()
        limiter = RateLimiter(max_queries=5, window_seconds=60, store=store)
        limiter.check("user1")
        assert store.count("user1", 60) == 1

    def test_default_user_id(self) -> None:
        limiter = RateLimiter(max_queries=5, window_seconds=60)
        result = limiter.check()
        assert result.allowed
