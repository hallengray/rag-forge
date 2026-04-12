"""Tests for AgenticQueryEngine with multi-query decomposition."""

import json
import tempfile
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.agentic import AgenticQueryEngine
from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


def _setup_engine() -> tuple[AgenticQueryEngine, MockEmbedder, QdrantStore]:
    with tempfile.TemporaryDirectory() as tmpdir:
        docs = Path(tmpdir) / "docs"
        docs.mkdir()
        (docs / "python.md").write_text("# Python\n\nPython is used for data science and web development.", encoding="utf-8")
        (docs / "rust.md").write_text("# Rust\n\nRust is used for systems programming and performance.", encoding="utf-8")

        embedder = MockEmbedder(dimension=384)
        store = QdrantStore()
        IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
            embedder=embedder, store=store, collection_name="test-agentic",
        ).run(docs)

        retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-agentic")
        decompose_response = json.dumps(["What is Python used for?", "What is Rust used for?"])
        generator = MockGenerator(fixed_response=decompose_response)

        engine = AgenticQueryEngine(retriever=retriever, generator=generator, top_k=5)
        return engine, embedder, store


class TestAgenticQueryEngine:
    def test_returns_query_result(self) -> None:
        engine, _, _ = _setup_engine()
        result = engine.query("Compare Python and Rust")
        assert result is not None
        assert len(result.answer) > 0
        assert result.chunks_retrieved > 0

    def test_decomposition_produces_sub_queries(self) -> None:
        engine, _, _ = _setup_engine()
        sub_queries = engine._decompose("Compare Python and Rust for data science")
        assert isinstance(sub_queries, list)
        assert len(sub_queries) == 2
        assert sub_queries[0] == "What is Python used for?"
        assert sub_queries[1] == "What is Rust used for?"

    def test_invalid_decomposition_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello world.", encoding="utf-8")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder, store=store, collection_name="test-fallback",
            ).run(docs)

            retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-fallback")
            engine = AgenticQueryEngine(retriever=retriever, generator=MockGenerator(), top_k=5)
            sub_queries = engine._decompose("What is Python?")
            assert sub_queries == ["What is Python?"]

    def test_merge_deduplicates_by_chunk_id(self) -> None:
        engine, _, _ = _setup_engine()
        results1 = [
            RetrievalResult(chunk_id="c1", text="Python", score=0.9, source_document="doc.md"),
            RetrievalResult(chunk_id="c2", text="Rust", score=0.8, source_document="doc.md"),
        ]
        results2 = [
            RetrievalResult(chunk_id="c1", text="Python", score=0.7, source_document="doc.md"),
            RetrievalResult(chunk_id="c3", text="Java", score=0.6, source_document="doc.md"),
        ]
        merged = engine._merge_results([results1, results2])
        chunk_ids = [r.chunk_id for r in merged]
        assert len(chunk_ids) == len(set(chunk_ids))
        c1 = next(r for r in merged if r.chunk_id == "c1")
        assert c1.score == 0.9

    def test_merge_sorts_by_score_descending(self) -> None:
        engine, _, _ = _setup_engine()
        results = [
            [RetrievalResult(chunk_id="c1", text="A", score=0.5, source_document="d")],
            [RetrievalResult(chunk_id="c2", text="B", score=0.9, source_document="d")],
        ]
        merged = engine._merge_results(results)
        scores = [r.score for r in merged]
        assert scores == sorted(scores, reverse=True)
