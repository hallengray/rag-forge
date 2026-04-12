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
        IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
            embedder=embedder, store=store, collection_name="test-cache",
        ).run(docs)

        retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-cache")
        return QueryEngine(retriever=retriever, generator=MockGenerator(), cache=cache)


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
