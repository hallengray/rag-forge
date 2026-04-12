"""Tests for instrumented IngestionPipeline with OpenTelemetry spans."""

import tempfile
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.storage.qdrant import QdrantStore


def _setup_tracer():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider


class TestInstrumentedPipeline:
    def test_emits_spans_when_tracer_set(self) -> None:
        exporter, provider = _setup_tracer()
        tracer = provider.get_tracer("test")

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello world.", encoding="utf-8")

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=MockEmbedder(dimension=384),
                store=QdrantStore(),
                collection_name="test-traced",
                tracer=tracer,
            )
            pipeline.run(docs)

        spans = exporter.get_finished_spans()
        span_names = [s.name for s in spans]
        assert "rag-forge.ingest" in span_names
        assert "rag-forge.parse" in span_names
        assert "rag-forge.chunk" in span_names
        assert "rag-forge.embed" in span_names
        assert "rag-forge.store" in span_names
        provider.shutdown()

    def test_parse_span_has_attributes(self) -> None:
        exporter, provider = _setup_tracer()
        tracer = provider.get_tracer("test")

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello world.", encoding="utf-8")

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=MockEmbedder(dimension=384),
                store=QdrantStore(),
                collection_name="test-traced",
                tracer=tracer,
            )
            pipeline.run(docs)

        spans = exporter.get_finished_spans()
        parse_span = next(s for s in spans if s.name == "rag-forge.parse")
        assert "document_count" in parse_span.attributes
        provider.shutdown()

    def test_no_spans_without_tracer(self) -> None:
        exporter, provider = _setup_tracer()

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello.", encoding="utf-8")

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=MockEmbedder(dimension=384),
                store=QdrantStore(),
            )
            pipeline.run(docs)

        spans = exporter.get_finished_spans()
        assert len(spans) == 0
        provider.shutdown()
