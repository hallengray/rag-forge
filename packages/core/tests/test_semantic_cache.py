"""Tests for semantic query caching."""

from rag_forge_core.context.semantic_cache import SemanticCache, _cosine_similarity
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.query.engine import QueryResult
from rag_forge_core.retrieval.base import RetrievalResult


def _sample_result() -> QueryResult:
    return QueryResult(
        answer="Python is a programming language.",
        sources=[RetrievalResult(chunk_id="c1", text="Python is a language.", score=0.95, source_document="doc.md")],
        model_used="mock-generator",
        chunks_retrieved=1,
    )


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 1.0

    def test_orthogonal_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_similar_vectors(self) -> None:
        assert _cosine_similarity([1.0, 1.0], [1.0, 0.9]) > 0.99

    def test_zero_vector(self) -> None:
        assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestSemanticCache:
    def test_exact_match_hit(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("What is Python?", _sample_result())
        cached = cache.get("What is Python?")
        assert cached is not None
        assert cached.answer == "Python is a programming language."

    def test_exact_match_case_insensitive(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("What is Python?", _sample_result())
        assert cache.get("what is python?") is not None

    def test_exact_match_strips_whitespace(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("  What is Python?  ", _sample_result())
        assert cache.get("What is Python?") is not None

    def test_cache_miss(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        assert cache.get("What is Rust?") is None

    def test_semantic_match_with_embedder(self) -> None:
        embedder = MockEmbedder(dimension=384)
        cache = SemanticCache(embedder=embedder, ttl_seconds=3600, similarity_threshold=0.5)
        cache.set("What is Python?", _sample_result())
        cached = cache.get("What is Python?")
        assert cached is not None

    def test_cache_miss_no_embedder(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        cache.set("What is Python?", _sample_result())
        assert cache.get("Tell me about Python") is None

    def test_ttl_expiry(self) -> None:
        cache = SemanticCache(ttl_seconds=0)
        cache.set("What is Python?", _sample_result())
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
        assert cache.stats["hits"] >= 1
        assert cache.stats["misses"] >= 1

    def test_result_serialization_round_trip(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        original = _sample_result()
        cache.set("test", original)
        cached = cache.get("test")
        assert cached is not None
        assert cached.answer == original.answer
        assert cached.model_used == original.model_used
        assert cached.chunks_retrieved == original.chunks_retrieved
        assert len(cached.sources) == 1
        assert cached.sources[0].chunk_id == "c1"

    def test_blocked_result_cached(self) -> None:
        cache = SemanticCache(ttl_seconds=3600)
        blocked = QueryResult(answer="", sources=[], model_used="mock", chunks_retrieved=0, blocked=True, blocked_reason="test")
        cache.set("blocked", blocked)
        cached = cache.get("blocked")
        assert cached is not None
        assert cached.blocked is True
