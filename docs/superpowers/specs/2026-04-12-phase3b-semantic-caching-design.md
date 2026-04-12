# Phase 3B: Semantic Caching Design Spec

## Context

RAG-Forge Phase 3A delivered OpenTelemetry observability. Phase 3B adds semantic caching to the query pipeline, reducing LLM costs by returning cached responses for semantically similar queries. The cache sits before retrieval in `QueryEngine` — a cache hit skips retrieval, generation, and guards entirely.

## Scope

**In scope:**
- `CacheStore` protocol with `InMemoryCacheStore` (default) and `RedisCacheStore` (optional dep)
- `SemanticCache` class with exact match + embedding cosine similarity lookup
- Configurable TTL (default 1 hour) for automatic expiry
- Configurable similarity threshold (default 0.95) for semantic matching
- `QueryEngine` integration as optional `cache` parameter
- Cache hit/miss OTEL span when tracing is active
- CLI flags: `--cache`, `--cache-ttl`, `--cache-similarity`
- Updated Python and TypeScript CLIs

**Out of scope:** Distributed cache invalidation, cache warming, cache analytics dashboard, multi-collection cache isolation.

## Architecture

The `SemanticCache` uses a two-tier lookup strategy. First, check for an exact string match (normalized, hashed — instant, free). If no exact match and an `EmbeddingProvider` is configured, embed the query and compute cosine similarity against all cached query embeddings. If any cached embedding exceeds the similarity threshold, return the cached result. Entries expire after the configured TTL.

```
QueryEngine.query("What is Python?")
    │
    ├─ 1. SemanticCache.get(query, embedder)
    │      ├─ Normalize query → hash key
    │      ├─ Exact match in store? → return cached QueryResult
    │      ├─ Embed query → cosine similarity scan
    │      │    └─ Similarity > 0.95? → return cached QueryResult
    │      └─ No match → return None (cache miss)
    │
    ├─ 2. [Cache miss] → InputGuard → Retrieve → Generate → OutputGuard
    │
    └─ 3. SemanticCache.set(query, result, query_embedding)
           └─ Store with TTL expiry
```

## Components

### 1. CacheStore Protocol and Implementations

**Location:** `packages/core/src/rag_forge_core/context/cache_store.py`

```python
from typing import Protocol, runtime_checkable


@dataclass
class CacheEntry:
    """A cached query result with metadata."""

    query: str
    query_embedding: list[float] | None
    result_json: str
    created_at: float
    ttl_seconds: int


@runtime_checkable
class CacheStore(Protocol):
    """Protocol for cache storage backends."""

    def get(self, key: str) -> CacheEntry | None:
        """Get a cache entry by key. Returns None if not found or expired."""
        ...

    def set(self, key: str, entry: CacheEntry) -> None:
        """Store a cache entry."""
        ...

    def delete(self, key: str) -> None:
        """Delete a cache entry."""
        ...

    def clear(self) -> None:
        """Clear all cache entries."""
        ...

    def all_entries(self) -> list[tuple[str, CacheEntry]]:
        """Return all non-expired entries for similarity scanning."""
        ...


class InMemoryCacheStore:
    """In-memory cache store. Resets on process restart."""

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> CacheEntry | None: ...
    def set(self, key: str, entry: CacheEntry) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...
    def all_entries(self) -> list[tuple[str, CacheEntry]]: ...


class RedisCacheStore:
    """Redis-backed cache store. Requires: pip install rag-forge-core[redis]

    Persists across restarts. Supports multi-process access.
    """

    def __init__(self, url: str = "redis://localhost:6379", prefix: str = "rag-forge:cache:") -> None:
        import redis
        self._client = redis.from_url(url)
        self._prefix = prefix

    def get(self, key: str) -> CacheEntry | None: ...
    def set(self, key: str, entry: CacheEntry) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...
    def all_entries(self) -> list[tuple[str, CacheEntry]]: ...
```

`InMemoryCacheStore.get()` checks `created_at + ttl_seconds` against current time. Expired entries are deleted on access (lazy expiry).

`RedisCacheStore` uses Redis TTL natively (`SETEX`). Entries are serialized as JSON. The `all_entries()` method scans keys with the prefix and deserializes — used for similarity search.

### 2. SemanticCache

**Location:** `packages/core/src/rag_forge_core/context/semantic_cache.py`

```python
import hashlib
import json
import math
import time
from dataclasses import dataclass

from rag_forge_core.context.cache_store import CacheEntry, CacheStore, InMemoryCacheStore
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.query.engine import QueryResult


class SemanticCache:
    """Semantic query cache with exact match + embedding similarity.

    Checks exact match first (free). Falls back to embedding cosine
    similarity when an embedder is provided.
    """

    def __init__(
        self,
        store: CacheStore | None = None,
        embedder: EmbeddingProvider | None = None,
        ttl_seconds: int = 3600,
        similarity_threshold: float = 0.95,
    ) -> None: ...

    def get(self, query: str) -> QueryResult | None:
        """Look up a cached result for the query."""
        ...

    def set(self, query: str, result: QueryResult) -> None:
        """Cache a query result."""
        ...

    def clear(self) -> None:
        """Clear all cached entries."""
        ...

    @property
    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        ...
```

Query normalization: `query.strip().lower()`

Hash key: `hashlib.sha256(normalized.encode()).hexdigest()`

Cosine similarity (pure Python, no numpy):
```python
def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
```

The `get()` method:
1. Normalize query, compute hash
2. Check exact match via `store.get(hash_key)`
3. If hit and not expired → deserialize and return `QueryResult`
4. If miss and `embedder` is not None:
   - Embed the query
   - Scan `store.all_entries()` for non-expired entries with embeddings
   - Compute cosine similarity for each
   - If best match > `similarity_threshold` → return that cached result
5. Return None (cache miss)

The `set()` method:
1. Normalize query, compute hash
2. If `embedder` is available, embed the query
3. Serialize `QueryResult` to JSON
4. Store as `CacheEntry` with current timestamp and TTL

Cache stats track `hits`, `misses`, `exact_hits`, `semantic_hits`.

### 3. QueryResult Serialization

`QueryResult` contains `list[RetrievalResult]` which has dataclass fields. For caching, we serialize to JSON:

```python
def _serialize_result(result: QueryResult) -> str:
    return json.dumps({
        "answer": result.answer,
        "model_used": result.model_used,
        "chunks_retrieved": result.chunks_retrieved,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "sources": [
            {"chunk_id": s.chunk_id, "text": s.text, "score": s.score,
             "source_document": s.source_document, "metadata": s.metadata}
            for s in result.sources
        ],
    })

def _deserialize_result(data: str) -> QueryResult:
    d = json.loads(data)
    return QueryResult(
        answer=d["answer"],
        sources=[RetrievalResult(**s) for s in d["sources"]],
        model_used=d["model_used"],
        chunks_retrieved=d["chunks_retrieved"],
        blocked=d.get("blocked", False),
        blocked_reason=d.get("blocked_reason"),
    )
```

### 4. QueryEngine Integration

**Location:** `packages/core/src/rag_forge_core/query/engine.py` (modify existing)

Add `cache: SemanticCache | None = None` to `__init__()`. In `query()`:

```python
def query(self, question, alpha=None, user_id="default"):
    # 0. Cache check (before guards — cached results already passed guards)
    if self._cache is not None:
        cached = self._cache.get(question)
        if cached is not None:
            # Emit cache hit span if tracing
            with self._span("rag-forge.cache_hit") as span:
                if span is not None:
                    span.set_attribute("cache_hit", True)
            return cached

    # 1. Input guard (existing)
    # 2. Retrieve (existing)
    # 3. Generate (existing)
    # 4. Output guard (existing)

    # 5. Cache store (after successful query)
    if self._cache is not None:
        self._cache.set(question, result)

    return result
```

Cache hits bypass guards because the original result already passed them. This is safe — the cached result was validated when it was first generated.

### 5. CLI Flags

**Location:** `packages/core/src/rag_forge_core/cli.py` (modify existing)

New args on query subparser:
- `--cache` (boolean flag) — enable in-memory caching
- `--cache-ttl <seconds>` (default: 3600) — TTL for cache entries
- `--cache-similarity <float>` (default: 0.95) — cosine similarity threshold

**Location:** `packages/cli/src/commands/query.ts` (modify existing)

Same flags forwarded to Python bridge.

### 6. Updated Context Module Exports

**Location:** `packages/core/src/rag_forge_core/context/__init__.py` (modify existing)

Export `SemanticCache`, `CacheStore`, `InMemoryCacheStore`, `RedisCacheStore`, `CacheEntry`.

## Dependencies

### New optional dependency (packages/core/pyproject.toml)

```toml
[project.optional-dependencies]
redis = ["redis>=5.0"]
```

No new required dependencies.

## Testing Strategy

### Unit Tests

1. `test_cache_store.py` — Test `InMemoryCacheStore` get/set/delete/clear/all_entries. Test TTL expiry. Test `RedisCacheStore` raises ImportError when redis not installed.

2. `test_semantic_cache.py` — Test exact match hit/miss. Test semantic similarity hit. Test TTL expiry. Test cache stats. Test with and without embedder. Test `_cosine_similarity` function.

3. `test_cached_query.py` — Test `QueryEngine` with cache: first query is a miss (normal pipeline runs), second identical query is a hit (pipeline skipped). Test cache bypass when cache is None.

## File Summary

### New files:
- `packages/core/src/rag_forge_core/context/cache_store.py`
- `packages/core/src/rag_forge_core/context/semantic_cache.py`
- `packages/core/tests/test_cache_store.py`
- `packages/core/tests/test_semantic_cache.py`
- `packages/core/tests/test_cached_query.py`

### Modified files:
- `packages/core/pyproject.toml` (add redis optional dep)
- `packages/core/src/rag_forge_core/context/__init__.py` (exports)
- `packages/core/src/rag_forge_core/query/engine.py` (add cache param)
- `packages/core/src/rag_forge_core/cli.py` (add cache CLI args)
- `packages/cli/src/commands/query.ts` (add cache flags)
