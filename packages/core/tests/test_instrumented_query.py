"""Tests for instrumented QueryEngine with OpenTelemetry spans."""

import tempfile
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.engine import QueryEngine
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


def _setup_tracer():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider


class TestInstrumentedQuery:
    def test_emits_spans_when_tracer_set(self) -> None:
        exporter, provider = _setup_tracer()
        tracer = provider.get_tracer("test")

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Python\n\nPython is a language.", encoding="utf-8")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder, store=store, collection_name="test-q-traced",
            ).run(docs)

            retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-q-traced")
            engine = QueryEngine(retriever=retriever, generator=MockGenerator(), tracer=tracer)
            engine.query("What is Python?")

        spans = exporter.get_finished_spans()
        span_names = [s.name for s in spans]
        assert "rag-forge.query" in span_names
        assert "rag-forge.retrieve" in span_names
        assert "rag-forge.generate" in span_names
        provider.shutdown()

    def test_no_spans_without_tracer(self) -> None:
        exporter, provider = _setup_tracer()

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello.", encoding="utf-8")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder, store=store, collection_name="test-notrace",
            ).run(docs)

            retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-notrace")
            engine = QueryEngine(retriever=retriever, generator=MockGenerator())
            engine.query("Hello?")

        spans = exporter.get_finished_spans()
        assert len(spans) == 0
        provider.shutdown()
