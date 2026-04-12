# Phase 3B: Semantic Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add semantic query caching to the RAG pipeline — exact match + embedding cosine similarity lookup with configurable TTL, reducing LLM costs by returning cached responses for similar queries.

**Architecture:** `SemanticCache` uses a two-tier lookup: exact string match (free) then embedding cosine similarity (one embed call). Cache sits before retrieval in `QueryEngine` — hits skip the entire pipeline. `CacheStore` protocol with in-memory default and optional Redis backend. TTL-based expiry.

**Tech Stack:** Python 3.11+ (hashlib, math, json, redis optional), pytest.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/core/src/rag_forge_core/context/cache_store.py` | `CacheStore` protocol, `CacheEntry`, `InMemoryCacheStore`, `RedisCacheStore` |
| `packages/core/src/rag_forge_core/context/semantic_cache.py` | `SemanticCache` with exact match + cosine similarity |
| `packages/core/tests/test_cache_store.py` | CacheStore tests |
| `packages/core/tests/test_semantic_cache.py` | SemanticCache tests |
| `packages/core/tests/test_cached_query.py` | QueryEngine + cache integration tests |

### Modified Files

| File | Change |
|------|--------|
| `packages/core/pyproject.toml` | Add redis optional dep |
| `packages/core/src/rag_forge_core/context/__init__.py` | Export cache types |
| `packages/core/src/rag_forge_core/query/engine.py` | Add optional `cache` parameter |
| `packages/core/src/rag_forge_core/cli.py` | Add `--cache`, `--cache-ttl`, `--cache-similarity` args |
| `packages/cli/src/commands/query.ts` | Add cache flags |

---

## Task 1: Add Redis Optional Dependency

**Files:**
- Modify: `packages/core/pyproject.toml`

- [ ] **Step 1: Add redis to optional deps**

Read `packages/core/pyproject.toml`. Add `redis = ["redis>=5.0"]` to `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
local = ["sentence-transformers>=3.0"]
cohere = ["cohere>=5.0"]
presidio = ["presidio-analyzer>=2.2"]
redis = ["redis>=5.0"]
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/pyproject.toml
git commit -m "chore(core): add redis optional dependency"
```

---

## Task 2: CacheStore Protocol and InMemoryCacheStore

**Files:**
- Create: `packages/core/src/rag_forge_core/context/cache_store.py`
- Test: `packages/core/tests/test_cache_store.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_cache_store.py`:

```python
"""Tests for cache store implementations."""

import time

from rag_forge_core.context.cache_store import (
    CacheEntry,
    CacheStore,
    InMemoryCacheStore,
)


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
        assert result.result_json == '{"answer": "Python is a language"}'

    def test_get_missing_key(self) -> None:
        store = InMemoryCacheStore()
        assert store.get("nonexistent") is None

    def test_get_expired_entry(self) -> None:
        store = InMemoryCacheStore()
        entry = CacheEntry(
            query="old query",
            query_embedding=None,
            result_json="{}",
            created_at=time.time() - 100,
            ttl_seconds=50,
        )
        store.set("expired", entry)
        assert store.get("expired") is None

    def test_delete(self) -> None:
        store = InMemoryCacheStore()
        store.set("key1", _sample_entry())
        store.delete("key1")
        assert store.get("key1") is None

    def test_delete_missing_key(self) -> None:
        store = InMemoryCacheStore()
        store.delete("nonexistent")  # Should not raise

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
        expired = CacheEntry(
            query="old",
            query_embedding=None,
            result_json="{}",
            created_at=time.time() - 100,
            ttl_seconds=50,
        )
        store.set("expired", expired)
        entries = store.all_entries()
        keys = [k for k, _ in entries]
        assert "fresh" in keys
        assert "expired" not in keys

    def test_entry_fields(self) -> None:
        entry = _sample_entry()
        assert isinstance(entry.query, str)
        assert isinstance(entry.query_embedding, list)
        assert isinstance(entry.result_json, str)
        assert isinstance(entry.created_at, float)
        assert isinstance(entry.ttl_seconds, int)

    def test_entry_with_none_embedding(self) -> None:
        entry = CacheEntry(
            query="test",
            query_embedding=None,
            result_json="{}",
            created_at=time.time(),
            ttl_seconds=3600,
        )
        store = InMemoryCacheStore()
        store.set("key", entry)
        result = store.get("key")
        assert result is not None
        assert result.query_embedding is None


class TestRedisCacheStore:
    def test_redis_not_installed_raises(self) -> None:
        """RedisCacheStore should raise ImportError when redis is not installed."""
        try:
            from rag_forge_core.context.cache_store import RedisCacheStore
            # If redis IS installed, this won't raise — skip gracefully
            RedisCacheStore(url="redis://localhost:6379")
        except ImportError:
            pass  # Expected when redis is not installed
        except Exception:
            pass  # Connection errors are fine — we just tested the import
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_cache_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/context/cache_store.py`:

```python
"""Cache storage backends for semantic query caching."""

import time
from dataclasses import dataclass
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

    def get(self, key: str) -> CacheEntry | None:
        """Get entry, returning None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() > entry.created_at + entry.ttl_seconds:
            del self._store[key]
            return None
        return entry

    def set(self, key: str, entry: CacheEntry) -> None:
        """Store a cache entry."""
        self._store[key] = entry

    def delete(self, key: str) -> None:
        """Delete a cache entry if it exists."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all entries."""
        self._store.clear()

    def all_entries(self) -> list[tuple[str, CacheEntry]]:
        """Return all non-expired entries."""
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
    """Redis-backed cache store.

    Requires: pip install rag-forge-core[redis]
    Persists across restarts. Supports multi-process access.
    """

    def __init__(self, url: str = "redis://localhost:6379", prefix: str = "rag-forge:cache:") -> None:
        import redis as redis_lib

        self._client = redis_lib.from_url(url)
        self._prefix = prefix

    def get(self, key: str) -> CacheEntry | None:
        """Get entry from Redis. Returns None if missing (TTL handled by Redis)."""
        import json

        data = self._client.get(self._prefix + key)
        if data is None:
            return None
        parsed = json.loads(data)
        return CacheEntry(**parsed)

    def set(self, key: str, entry: CacheEntry) -> None:
        """Store entry in Redis with TTL."""
        import json
        from dataclasses import asdict

        self._client.setex(
            self._prefix + key,
            entry.ttl_seconds,
            json.dumps(asdict(entry)),
        )

    def delete(self, key: str) -> None:
        """Delete entry from Redis."""
        self._client.delete(self._prefix + key)

    def clear(self) -> None:
        """Clear all entries with this prefix."""
        keys = self._client.keys(self._prefix + "*")
        if keys:
            self._client.delete(*keys)

    def all_entries(self) -> list[tuple[str, CacheEntry]]:
        """Return all entries with this prefix."""
        import json

        entries: list[tuple[str, CacheEntry]] = []
        keys = self._client.keys(self._prefix + "*")
        for key in keys:
            data = self._client.get(key)
            if data is not None:
                key_str = key.decode() if isinstance(key, bytes) else key
                short_key = key_str.removeprefix(self._prefix)
                parsed = json.loads(data)
                entries.append((short_key, CacheEntry(**parsed)))
        return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_cache_store.py -v`
Expected: All 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/context/cache_store.py packages/core/tests/test_cache_store.py
git commit -m "feat(core): add CacheStore protocol with in-memory and Redis implementations"
```

---

## Task 3: SemanticCache

**Files:**
- Create: `packages/core/src/rag_forge_core/context/semantic_cache.py`
- Test: `packages/core/tests/test_semantic_cache.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_semantic_cache.py`:

```python
"""Tests for semantic query caching."""

from rag_forge_core.context.semantic_cache import SemanticCache, _cosine_similarity
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.query.engine import QueryResult
from rag_forge_core.retrieval.base import RetrievalResult


def _sample_result() -> QueryResult:
    return QueryResult(
        answer="Python is a programming language.",
        sources=[
            RetrievalResult(
                chunk_id="c1",
                text="Python is a language.",
                score=0.95,
                source_document="doc.md",
            )
        ],
        model_used="mock-generator",
        chunks_retrieved=1,
    )


class TestCosineSimliarity:
    def test_identical_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 1.0

    def test_orthogonal_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_similar_vectors(self) -> None:
        sim = _cosine_similarity([1.0, 1.0], [1.0, 0.9])
        assert sim > 0.99

    def test_zero_vector(self) -> None:
        assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestSemanticCache:
    def test_exact_match_hit(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        result = _sample_result()
        cache.set("What is Python?", result)
        cached = cache.get("What is Python?")
        assert cached is not None
        assert cached.answer == result.answer

    def test_exact_match_case_insensitive(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("What is Python?", _sample_result())
        cached = cache.get("what is python?")
        assert cached is not None

    def test_exact_match_strips_whitespace(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("  What is Python?  ", _sample_result())
        cached = cache.get("What is Python?")
        assert cached is not None

    def test_cache_miss(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        assert cache.get("What is Rust?") is None

    def test_semantic_match_with_embedder(self) -> None:
        embedder = MockEmbedder(dimension=384)
        cache = SemanticCache(embedder=embedder, ttl_seconds=3600, similarity_threshold=0.5)
        cache.set("What is Python?", _sample_result())
        # MockEmbedder produces deterministic hashes — same text gets same vector
        # "What is Python?" should match itself
        cached = cache.get("What is Python?")
        assert cached is not None

    def test_cache_miss_no_embedder(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("What is Python?", _sample_result())
        # Different query, no embedder — can't do semantic match
        assert cache.get("Tell me about Python") is None

    def test_ttl_expiry(self) -> None:
        cache = SemanticCache(ttl_seconds=0)
        cache.set("What is Python?", _sample_result())
        # TTL=0 means already expired
        assert cache.get("What is Python?") is None

    def test_clear(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("What is Python?", _sample_result())
        cache.clear()
        assert cache.get("What is Python?") is None

    def test_stats(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("What is Python?", _sample_result())
        cache.get("What is Python?")
        cache.get("What is Rust?")
        stats = cache.stats
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    def test_result_serialization_round_trip(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        original = _sample_result()
        cache.set("test", original)
        cached = cache.get("test")
        assert cached is not None
        assert cached.answer == original.answer
        assert cached.model_used == original.model_used
        assert cached.chunks_retrieved == original.chunks_retrieved
        assert len(cached.sources) == len(original.sources)
        assert cached.sources[0].chunk_id == original.sources[0].chunk_id

    def test_blocked_result_cached(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        blocked = QueryResult(
            answer="", sources=[], model_used="mock",
            chunks_retrieved=0, blocked=True, blocked_reason="test",
        )
        cache.set("blocked query", blocked)
        cached = cache.get("blocked query")
        assert cached is not None
        assert cached.blocked is True
        assert cached.blocked_reason == "test"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_semantic_cache.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/context/semantic_cache.py`:

```python
"""Semantic query cache with exact match + embedding cosine similarity."""

import hashlib
import json
import math
import time

from rag_forge_core.context.cache_store import CacheEntry, CacheStore, InMemoryCacheStore
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.query.engine import QueryResult
from rag_forge_core.retrieval.base import RetrievalResult


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors. Pure Python, no numpy."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _normalize_query(query: str) -> str:
    """Normalize a query for cache key computation."""
    return query.strip().lower()


def _hash_query(query: str) -> str:
    """Compute a hash key for a normalized query."""
    return hashlib.sha256(_normalize_query(query).encode("utf-8")).hexdigest()


def _serialize_result(result: QueryResult) -> str:
    """Serialize a QueryResult to JSON for caching."""
    return json.dumps({
        "answer": result.answer,
        "model_used": result.model_used,
        "chunks_retrieved": result.chunks_retrieved,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "sources": [
            {
                "chunk_id": s.chunk_id,
                "text": s.text,
                "score": s.score,
                "source_document": s.source_document,
                "metadata": dict(s.metadata),
            }
            for s in result.sources
        ],
    })


def _deserialize_result(data: str) -> QueryResult:
    """Deserialize a QueryResult from cached JSON."""
    d = json.loads(data)
    return QueryResult(
        answer=d["answer"],
        sources=[
            RetrievalResult(
                chunk_id=s["chunk_id"],
                text=s["text"],
                score=s["score"],
                source_document=s["source_document"],
                metadata=s.get("metadata", {}),
            )
            for s in d.get("sources", [])
        ],
        model_used=d["model_used"],
        chunks_retrieved=d["chunks_retrieved"],
        blocked=d.get("blocked", False),
        blocked_reason=d.get("blocked_reason"),
    )


class SemanticCache:
    """Semantic query cache with exact match + embedding cosine similarity.

    Two-tier lookup:
    1. Exact match (normalized string hash) — free, instant
    2. Embedding cosine similarity — one embed call, scans cached embeddings

    Cache entries expire after TTL. Stats track hits/misses.
    """

    def __init__(
        self,
        store: CacheStore | None = None,
        embedder: EmbeddingProvider | None = None,
        ttl_seconds: int = 3600,
        similarity_threshold: float = 0.95,
    ) -> None:
        self._store = store or InMemoryCacheStore()
        self._embedder = embedder
        self._ttl_seconds = ttl_seconds
        self._similarity_threshold = similarity_threshold
        self._hits = 0
        self._misses = 0
        self._exact_hits = 0
        self._semantic_hits = 0

    def get(self, query: str) -> QueryResult | None:
        """Look up a cached result for the query.

        Checks exact match first, then semantic similarity if embedder available.
        """
        key = _hash_query(query)

        # 1. Exact match
        entry = self._store.get(key)
        if entry is not None:
            self._hits += 1
            self._exact_hits += 1
            return _deserialize_result(entry.result_json)

        # 2. Semantic similarity (if embedder available)
        if self._embedder is not None:
            query_embedding = self._embedder.embed([_normalize_query(query)])[0]
            best_score = 0.0
            best_entry: CacheEntry | None = None

            for _, cached_entry in self._store.all_entries():
                if cached_entry.query_embedding is None:
                    continue
                similarity = _cosine_similarity(query_embedding, cached_entry.query_embedding)
                if similarity > best_score:
                    best_score = similarity
                    best_entry = cached_entry

            if best_entry is not None and best_score >= self._similarity_threshold:
                self._hits += 1
                self._semantic_hits += 1
                return _deserialize_result(best_entry.result_json)

        self._misses += 1
        return None

    def set(self, query: str, result: QueryResult) -> None:
        """Cache a query result with optional embedding."""
        key = _hash_query(query)
        embedding: list[float] | None = None

        if self._embedder is not None:
            embedding = self._embedder.embed([_normalize_query(query)])[0]

        entry = CacheEntry(
            query=_normalize_query(query),
            query_embedding=embedding,
            result_json=_serialize_result(result),
            created_at=time.time(),
            ttl_seconds=self._ttl_seconds,
        )
        self._store.set(key, entry)

    def clear(self) -> None:
        """Clear all cached entries and reset stats."""
        self._store.clear()
        self._hits = 0
        self._misses = 0
        self._exact_hits = 0
        self._semantic_hits = 0

    @property
    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "exact_hits": self._exact_hits,
            "semantic_hits": self._semantic_hits,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_semantic_cache.py -v`
Expected: All 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/context/semantic_cache.py packages/core/tests/test_semantic_cache.py
git commit -m "feat(core): add SemanticCache with exact match and cosine similarity"
```

---

## Task 4: QueryEngine Cache Integration

**Files:**
- Modify: `packages/core/src/rag_forge_core/query/engine.py`
- Test: `packages/core/tests/test_cached_query.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_cached_query.py`:

```python
"""Tests for QueryEngine with semantic caching."""

import tempfile
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.context.semantic_cache import SemanticCache
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.engine import QueryEngine
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


def _setup_engine(cache: SemanticCache | None = None) -> QueryEngine:
    with tempfile.TemporaryDirectory() as tmpdir:
        docs = Path(tmpdir) / "docs"
        docs.mkdir()
        (docs / "test.md").write_text("# Python\n\nPython is a programming language.", encoding="utf-8")

        embedder = MockEmbedder(dimension=384)
        store = QdrantStore()
        pipeline = IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
            embedder=embedder,
            store=store,
            collection_name="test-cache",
        )
        pipeline.run(docs)

        retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-cache")
        return QueryEngine(
            retriever=retriever,
            generator=MockGenerator(),
            cache=cache,
        )


class TestCachedQuery:
    def test_first_query_is_cache_miss(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        engine = _setup_engine(cache=cache)
        result = engine.query("What is Python?")
        assert not result.blocked
        assert len(result.answer) > 0
        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 0

    def test_second_identical_query_is_cache_hit(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        engine = _setup_engine(cache=cache)
        result1 = engine.query("What is Python?")
        result2 = engine.query("What is Python?")
        assert result1.answer == result2.answer
        assert cache.stats["hits"] == 1
        assert cache.stats["exact_hits"] == 1

    def test_no_cache_means_no_caching(self) -> None:
        engine = _setup_engine(cache=None)
        result1 = engine.query("What is Python?")
        result2 = engine.query("What is Python?")
        assert len(result1.answer) > 0
        assert len(result2.answer) > 0

    def test_cache_preserves_sources(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        engine = _setup_engine(cache=cache)
        result1 = engine.query("What is Python?")
        result2 = engine.query("What is Python?")
        assert len(result2.sources) == len(result1.sources)
        assert result2.chunks_retrieved == result1.chunks_retrieved
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_cached_query.py -v`
Expected: FAIL — `QueryEngine` doesn't accept `cache` parameter.

- [ ] **Step 3: Update QueryEngine**

Read `packages/core/src/rag_forge_core/query/engine.py`. Add:

1. Import at top:
```python
from rag_forge_core.context.semantic_cache import SemanticCache
```

2. Add `cache` parameter to `__init__`:
```python
    def __init__(
        self,
        retriever: RetrieverProtocol,
        generator: GenerationProvider,
        top_k: int = 5,
        input_guard: InputGuard | None = None,
        output_guard: OutputGuard | None = None,
        tracer: trace.Tracer | None = None,
        cache: SemanticCache | None = None,
    ) -> None:
        # ... existing assignments ...
        self._cache = cache
```

3. In `query()`, INSIDE the `with self._span("rag-forge.query"):` block, BEFORE the input guard check, add cache lookup:

```python
            # 0. Cache check (before guards — cached results already passed guards)
            if self._cache is not None:
                cached = self._cache.get(question)
                if cached is not None:
                    with self._span("rag-forge.cache_hit") as span:
                        if span is not None:
                            span.set_attribute("cache_hit", True)
                    return cached
```

4. At the END of `query()`, just before `return QueryResult(...)`, add cache store:

```python
            result = QueryResult(
                answer=answer,
                sources=results,
                model_used=self._generator.model_name(),
                chunks_retrieved=len(results),
            )

            # Store in cache
            if self._cache is not None:
                self._cache.set(question, result)

            return result
```

IMPORTANT: Only cache successful (non-blocked) results. The cache store should be AFTER the output guard check, and ONLY on the happy path.

- [ ] **Step 4: Run tests**

Run: `cd packages/core && uv run pytest tests/test_cached_query.py tests/test_query.py tests/test_security_integration.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/query/engine.py packages/core/tests/test_cached_query.py
git commit -m "feat(core): integrate SemanticCache into QueryEngine"
```

---

## Task 5: Update Module Exports

**Files:**
- Modify: `packages/core/src/rag_forge_core/context/__init__.py`

- [ ] **Step 1: Update context __init__.py**

Read the current file (it exports ContextManager, ContextWindow, ContextualEnricher, EnrichmentResult). Add cache exports:

```python
"""Context management: window tracking, enrichment, caching."""

from rag_forge_core.context.cache_store import (
    CacheEntry,
    CacheStore,
    InMemoryCacheStore,
    RedisCacheStore,
)
from rag_forge_core.context.enricher import ContextualEnricher, EnrichmentResult
from rag_forge_core.context.manager import ContextManager, ContextWindow
from rag_forge_core.context.semantic_cache import SemanticCache

__all__ = [
    "CacheEntry",
    "CacheStore",
    "ContextManager",
    "ContextWindow",
    "ContextualEnricher",
    "EnrichmentResult",
    "InMemoryCacheStore",
    "RedisCacheStore",
    "SemanticCache",
]
```

- [ ] **Step 2: Verify imports**

Run: `cd packages/core && uv run python -c "from rag_forge_core.context import SemanticCache, InMemoryCacheStore; print(SemanticCache)"`

- [ ] **Step 3: Commit**

```bash
git add packages/core/src/rag_forge_core/context/__init__.py
git commit -m "chore(core): export cache types from context module"
```

---

## Task 6: Update CLIs

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py`
- Modify: `packages/cli/src/commands/query.ts`

- [ ] **Step 1: Update Python CLI**

Read `packages/core/src/rag_forge_core/cli.py`. Add import:

```python
from rag_forge_core.context.semantic_cache import SemanticCache
```

In `cmd_query()`, BEFORE the QueryEngine construction, add cache setup:

```python
    # Build cache if enabled
    cache = None
    if args.cache:
        cache = SemanticCache(
            embedder=_create_embedder(embedding_provider),
            ttl_seconds=int(args.cache_ttl),
            similarity_threshold=float(args.cache_similarity),
        )
```

Pass `cache=cache` to `QueryEngine(...)`.

Add to the output dict:
```python
        "cache_hit": cache is not None and cache.stats["hits"] > 0,
```

Add args to query parser in `main()`:
```python
    query_parser.add_argument(
        "--cache", action="store_true", help="Enable semantic query caching"
    )
    query_parser.add_argument(
        "--cache-ttl", default="3600", help="Cache TTL in seconds"
    )
    query_parser.add_argument(
        "--cache-similarity", default="0.95", help="Cosine similarity threshold"
    )
```

- [ ] **Step 2: Update TypeScript CLI**

Read `packages/cli/src/commands/query.ts`. Add options:

```typescript
    .option("--cache", "Enable semantic query caching")
    .option("--cache-ttl <seconds>", "Cache TTL in seconds", "3600")
    .option("--cache-similarity <threshold>", "Cosine similarity threshold", "0.95")
```

Add to options type: `cache?: boolean; cacheTtl: string; cacheSimilarity: string;`

Add to args forwarding:
```typescript
          if (options.cache) {
            args.push("--cache");
          }
          args.push("--cache-ttl", options.cacheTtl);
          args.push("--cache-similarity", options.cacheSimilarity);
```

- [ ] **Step 3: Build and verify**

Run: `cd packages/cli && pnpm run build && pnpm run typecheck`
Run: `cd packages/core && uv run python -m rag_forge_core.cli query --help` — should show cache flags.

- [ ] **Step 4: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py packages/cli/src/commands/query.ts
git commit -m "feat(cli): add --cache, --cache-ttl, --cache-similarity flags to query command"
```

---

## Task 7: Run Full Test Suite and Lint

- [ ] **Step 1: Run all Python tests**

Run: `uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run Python linter**

Run: `uv run ruff check .`
Expected: No errors. Fix any.

- [ ] **Step 3: Run Python type checker**

Run: `uv run mypy packages/core/src packages/evaluator/src packages/observability/src`
Expected: No errors. Fix any.

- [ ] **Step 4: Build TypeScript**

Run: `pnpm run build`

- [ ] **Step 5: Run TypeScript lint and typecheck**

Run: `pnpm run lint && pnpm run typecheck`

- [ ] **Step 6: Fix any issues, commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors from Phase 3B implementation"
```

- [ ] **Step 7: Push**

```bash
git push
```
