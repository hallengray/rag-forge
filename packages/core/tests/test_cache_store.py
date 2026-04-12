"""Tests for cache store implementations."""

import time

from rag_forge_core.context.cache_store import CacheEntry, CacheStore, InMemoryCacheStore


def _sample_entry(ttl: int = 3600) -> CacheEntry:
    return CacheEntry(
        query="what is python",
        query_embedding=[0.1, 0.2, 0.3],
        result_json='{"answer": "Python is a language"}',
        created_at=time.time(),
        ttl_seconds=ttl,
    )


class TestInMemoryCacheStore:
    def test_implements_protocol(self) -> None:
        assert isinstance(InMemoryCacheStore(), CacheStore)

    def test_set_and_get(self) -> None:
        store = InMemoryCacheStore()
        entry = _sample_entry()
        store.set("key1", entry)
        result = store.get("key1")
        assert result is not None
        assert result.query == "what is python"

    def test_get_missing_key(self) -> None:
        store = InMemoryCacheStore()
        assert store.get("nonexistent") is None

    def test_get_expired_entry(self) -> None:
        store = InMemoryCacheStore()
        entry = CacheEntry(query="old", query_embedding=None, result_json="{}", created_at=time.time() - 100, ttl_seconds=50)
        store.set("expired", entry)
        assert store.get("expired") is None

    def test_delete(self) -> None:
        store = InMemoryCacheStore()
        store.set("key1", _sample_entry())
        store.delete("key1")
        assert store.get("key1") is None

    def test_delete_missing_key(self) -> None:
        store = InMemoryCacheStore()
        store.delete("nonexistent")

    def test_clear(self) -> None:
        store = InMemoryCacheStore()
        store.set("key1", _sample_entry())
        store.set("key2", _sample_entry())
        store.clear()
        assert store.get("key1") is None
        assert store.get("key2") is None

    def test_all_entries_returns_non_expired(self) -> None:
        store = InMemoryCacheStore()
        store.set("fresh", _sample_entry(ttl=3600))
        expired = CacheEntry(query="old", query_embedding=None, result_json="{}", created_at=time.time() - 100, ttl_seconds=50)
        store.set("expired", expired)
        entries = store.all_entries()
        keys = [k for k, _ in entries]
        assert "fresh" in keys
        assert "expired" not in keys

    def test_entry_with_none_embedding(self) -> None:
        entry = CacheEntry(query="test", query_embedding=None, result_json="{}", created_at=time.time(), ttl_seconds=3600)
        store = InMemoryCacheStore()
        store.set("key", entry)
        result = store.get("key")
        assert result is not None
        assert result.query_embedding is None
