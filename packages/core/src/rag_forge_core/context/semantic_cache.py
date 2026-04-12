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
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _normalize_query(query: str) -> str:
    return query.strip().lower()


def _hash_query(query: str) -> str:
    return hashlib.sha256(_normalize_query(query).encode("utf-8")).hexdigest()


def _serialize_result(result: QueryResult) -> str:
    return json.dumps({
        "answer": result.answer,
        "model_used": result.model_used,
        "chunks_retrieved": result.chunks_retrieved,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "sources": [
            {"chunk_id": s.chunk_id, "text": s.text, "score": s.score,
             "source_document": s.source_document, "metadata": dict(s.metadata)}
            for s in result.sources
        ],
    })


def _deserialize_result(data: str) -> QueryResult:
    d = json.loads(data)
    return QueryResult(
        answer=d["answer"],
        sources=[
            RetrievalResult(chunk_id=s["chunk_id"], text=s["text"], score=s["score"],
                           source_document=s["source_document"], metadata=s.get("metadata", {}))
            for s in d.get("sources", [])
        ],
        model_used=d["model_used"],
        chunks_retrieved=d["chunks_retrieved"],
        blocked=d.get("blocked", False),
        blocked_reason=d.get("blocked_reason"),
    )


class SemanticCache:
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
        key = _hash_query(query)
        entry = self._store.get(key)
        if entry is not None:
            self._hits += 1
            self._exact_hits += 1
            return _deserialize_result(entry.result_json)

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
        self._store.clear()
        self._hits = 0
        self._misses = 0
        self._exact_hits = 0
        self._semantic_hits = 0

    @property
    def stats(self) -> dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "exact_hits": self._exact_hits, "semantic_hits": self._semantic_hits}
