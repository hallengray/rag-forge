"""Tests for the generation providers and query engine."""

from pathlib import Path

from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.engine import QueryEngine, QueryResult
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


class TestMockGenerator:
    def test_implements_protocol(self) -> None:
        assert isinstance(MockGenerator(), GenerationProvider)

    def test_returns_fixed_response(self) -> None:
        gen = MockGenerator(fixed_response="The answer is 42.")
        assert gen.generate("system", "user") == "The answer is 42."

    def test_default_response(self) -> None:
        assert len(MockGenerator().generate("system", "question")) > 0

    def test_model_name(self) -> None:
        assert MockGenerator().model_name() == "mock-generator"


class TestQueryEngine:
    def _index_docs(self, tmp_path: Path) -> tuple[MockEmbedder, QdrantStore]:
        (tmp_path / "doc.md").write_text(
            "# Python Guide\n\nPython is a programming language used for "
            "data science, web development, and automation.",
            encoding="utf-8",
        )
        embedder = MockEmbedder()
        store = QdrantStore()
        pipeline = IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(),
            embedder=embedder,
            store=store,
            collection_name="test-query",
        )
        pipeline.run(tmp_path)
        return embedder, store

    def test_query_returns_result(self, tmp_path: Path) -> None:
        embedder, store = self._index_docs(tmp_path)
        retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-query")
        engine = QueryEngine(retriever=retriever, generator=MockGenerator())
        result = engine.query("What is Python?")
        assert isinstance(result, QueryResult)
        assert len(result.answer) > 0
        assert result.chunks_retrieved > 0
        assert len(result.sources) > 0

    def test_query_includes_sources(self, tmp_path: Path) -> None:
        embedder, store = self._index_docs(tmp_path)
        retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-query")
        engine = QueryEngine(retriever=retriever, generator=MockGenerator())
        result = engine.query("What is Python?")
        assert all(hasattr(s, "text") for s in result.sources)
        assert all(hasattr(s, "chunk_id") for s in result.sources)
        assert all(hasattr(s, "source_document") for s in result.sources)

    def test_query_respects_top_k(self, tmp_path: Path) -> None:
        embedder, store = self._index_docs(tmp_path)
        retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-query")
        engine = QueryEngine(retriever=retriever, generator=MockGenerator(), top_k=1)
        result = engine.query("What is Python?")
        assert result.chunks_retrieved <= 1

    def test_query_empty_collection(self) -> None:
        embedder = MockEmbedder()
        store = QdrantStore()
        store.create_collection("empty", dimension=embedder.dimension())
        retriever = DenseRetriever(embedder=embedder, store=store, collection_name="empty")
        engine = QueryEngine(retriever=retriever, generator=MockGenerator())
        result = engine.query("anything")
        assert result.chunks_retrieved == 0
