"""Tests for contextual enrichment (document summary prepending)."""

from rag_forge_core.chunking.base import Chunk
from rag_forge_core.context.enricher import ContextualEnricher, EnrichmentResult
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.parsing.base import Document


def _sample_document() -> Document:
    return Document(
        text="Python is a versatile programming language used for web development, "
        "data science, machine learning, and automation. It was created by "
        "Guido van Rossum and first released in 1991.",
        source_path="docs/python.md",
        metadata={"title": "Python Overview"},
    )


def _sample_chunks(source: str = "docs/python.md") -> list[Chunk]:
    return [
        Chunk(
            text="Python is a versatile programming language used for web development.",
            chunk_index=0,
            source_document=source,
            strategy_used="recursive",
        ),
        Chunk(
            text="It was created by Guido van Rossum and first released in 1991.",
            chunk_index=1,
            source_document=source,
            strategy_used="recursive",
        ),
    ]


class TestContextualEnricher:
    def test_enrich_returns_same_count(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        assert len(enriched) == len(chunks)

    def test_enriched_text_contains_original(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for original, result in zip(chunks, enriched, strict=True):
            assert original.text in result.text

    def test_enriched_text_has_context_prefix(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for chunk in enriched:
            assert chunk.text.startswith("[Document context:")

    def test_original_text_preserved_in_metadata(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for original, result in zip(chunks, enriched, strict=True):
            assert result.metadata is not None
            assert result.metadata["original_text"] == original.text

    def test_summary_stored_in_metadata(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for chunk in enriched:
            assert chunk.metadata is not None
            assert "document_summary" in chunk.metadata
            assert isinstance(chunk.metadata["document_summary"], str)
            assert len(str(chunk.metadata["document_summary"])) > 0

    def test_chunk_index_preserved(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for original, result in zip(chunks, enriched, strict=True):
            assert result.chunk_index == original.chunk_index
            assert result.source_document == original.source_document
            assert result.strategy_used == original.strategy_used

    def test_empty_chunks_returns_empty(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        enriched = enricher.enrich(doc, [])
        assert enriched == []

    def test_summary_called_once_per_document(self) -> None:
        """The generator should be called exactly once per enrich() call."""
        call_count = 0
        original_generate = MockGenerator.generate

        def counting_generate(self_gen: MockGenerator, system: str, user: str) -> str:
            nonlocal call_count
            call_count += 1
            return original_generate(self_gen, system, user)

        generator = MockGenerator()
        generator.generate = counting_generate.__get__(generator, MockGenerator)  # type: ignore[assignment]
        enricher = ContextualEnricher(generator=generator)
        doc = _sample_document()
        chunks = _sample_chunks()
        enricher.enrich(doc, chunks)
        assert call_count == 1
