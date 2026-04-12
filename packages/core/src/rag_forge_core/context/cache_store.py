"""Cache storage backends for semantic query caching."""

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class CacheEntry:
    query: str
    query_embedding: list[float] | None
    result_json: str
    created_at: float
    ttl_seconds: int


@runtime_checkable
class CacheStore(Protocol):
    def get(self, key: str) -> CacheEntry | None: ...
    def set(self, key: str, entry: CacheEntry) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...
    def all_entries(self) -> list[tuple[str, CacheEntry]]: ...


class InMemoryCacheStore:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> CacheEntry | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() > entry.created_at + entry.ttl_seconds:
            del self._store[key]
            return None
        return entry

    def set(self, key: str, entry: CacheEntry) -> None:
        self._store[key] = entry

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def all_entries(self) -> list[tuple[str, CacheEntry]]:
        now = time.time()
        valid: list[tuple[str, CacheEntry]] = []
        expired_keys: list[str] = []
        for key, entry in self._store.items():
            if now > entry.created_at + entry.ttl_seconds:
                expired_keys.append(key)
            else:
                valid.append((key, entry))
        for key in expired_keys:
            del self._store[key]
        return valid


class RedisCacheStore:
    def __init__(self, url: str = "redis://localhost:6379", prefix: str = "rag-forge:cache:") -> None:
        import redis as redis_lib
        self._client = redis_lib.from_url(url)
        self._prefix = prefix

    def get(self, key: str) -> CacheEntry | None:
        import json
        data = self._client.get(self._prefix + key)
        if data is None:
            return None
        parsed = json.loads(data)
        return CacheEntry(**parsed)

    def set(self, key: str, entry: CacheEntry) -> None:
        import json
        from dataclasses import asdict
        self._client.setex(self._prefix + key, entry.ttl_seconds, json.dumps(asdict(entry)))

    def delete(self, key: str) -> None:
        self._client.delete(self._prefix + key)

    def clear(self) -> None:
        keys = self._client.keys(self._prefix + "*")
        if keys:
            self._client.delete(*keys)

    def all_entries(self) -> list[tuple[str, CacheEntry]]:
        import json
        entries: list[tuple[str, CacheEntry]] = []
        keys = self._client.keys(self._prefix + "*")
        for key in keys:
            data = self._client.get(key)
            if data is not None:
                key_str = key.decode() if isinstance(key, bytes) else key
                short_key = key_str.removeprefix(self._prefix)
                entries.append((short_key, CacheEntry(**json.loads(data))))
        return entries
