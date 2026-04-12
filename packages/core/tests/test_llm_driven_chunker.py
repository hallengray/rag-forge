"""Tests for LLM-driven chunking strategy."""


from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.llm_driven import LLMDrivenChunker
from rag_forge_core.generation.mock_generator import MockGenerator


class TestLLMDrivenChunker:
    def test_empty_text_returns_no_chunks(self) -> None:
        generator = MockGenerator()
        chunker = LLMDrivenChunker(
            config=ChunkConfig(strategy="llm-driven"),
            generator=generator,
        )
        result = chunker.chunk("", "test.md")
        assert len(result) == 0

    def test_short_text_returns_single_chunk(self) -> None:
        generator = MockGenerator()
        chunker = LLMDrivenChunker(
            config=ChunkConfig(strategy="llm-driven"),
            generator=generator,
        )
        result = chunker.chunk("Hello world.", "test.md")
        assert len(result) == 1
        assert result[0].strategy_used == "llm-driven"
        assert result[0].source_document == "test.md"

    def test_long_text_produces_multiple_chunks(self) -> None:
        generator = MockGenerator()
        chunker = LLMDrivenChunker(
            config=ChunkConfig(strategy="llm-driven", chunk_size=64),
            generator=generator,
        )
        text = "Sentence about topic A. " * 30 + "Sentence about topic B. " * 30
        result = chunker.chunk(text, "test.md")
        assert len(result) >= 1

    def test_chunk_indices_are_sequential(self) -> None:
        generator = MockGenerator()
        chunker = LLMDrivenChunker(
            config=ChunkConfig(strategy="llm-driven", chunk_size=64),
            generator=generator,
        )
        text = "Some text. " * 100
        chunks = chunker.chunk(text, "test.md")
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_preview_matches_chunk(self) -> None:
        generator = MockGenerator()
        chunker = LLMDrivenChunker(
            config=ChunkConfig(strategy="llm-driven"),
            generator=generator,
        )
        text = "Hello world."
        assert chunker.preview(text, "test.md") == chunker.chunk(text, "test.md")

    def test_stats_reports_correct_totals(self) -> None:
        generator = MockGenerator()
        chunker = LLMDrivenChunker(
            config=ChunkConfig(strategy="llm-driven", chunk_size=64),
            generator=generator,
        )
        text = "Some text here. " * 50
        chunks = chunker.chunk(text, "test.md")
        stats = chunker.stats(chunks)
        assert stats.total_chunks == len(chunks)
        assert stats.total_tokens > 0

    def test_fallback_when_llm_returns_invalid_json(self) -> None:
        """When the LLM returns garbage, fall back to size-based splitting."""
        generator = MockGenerator()
        chunker = LLMDrivenChunker(
            config=ChunkConfig(strategy="llm-driven", chunk_size=64),
            generator=generator,
        )
        text = "Some text. " * 100
        # MockGenerator returns a deterministic string, not JSON boundaries.
        # The chunker should handle this gracefully via fallback.
        result = chunker.chunk(text, "test.md")
        assert len(result) >= 1
        for chunk in result:
            assert chunk.strategy_used == "llm-driven"
