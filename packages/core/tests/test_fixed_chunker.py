"""Tests for fixed-size chunking strategy."""

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.fixed import FixedSizeChunker


class TestFixedSizeChunker:
    def test_empty_text_returns_no_chunks(self) -> None:
        chunker = FixedSizeChunker(ChunkConfig(strategy="fixed", chunk_size=64, overlap_ratio=0.0))
        result = chunker.chunk("", "test.md")
        assert len(result) == 0

    def test_whitespace_only_returns_no_chunks(self) -> None:
        chunker = FixedSizeChunker(ChunkConfig(strategy="fixed", chunk_size=64, overlap_ratio=0.0))
        result = chunker.chunk("   \n\t  ", "test.md")
        assert len(result) == 0

    def test_short_text_returns_single_chunk(self) -> None:
        chunker = FixedSizeChunker(ChunkConfig(strategy="fixed", chunk_size=512, overlap_ratio=0.0))
        result = chunker.chunk("Hello world.", "test.md")
        assert len(result) == 1
        assert result[0].text == "Hello world."
        assert result[0].source_document == "test.md"
        assert result[0].strategy_used == "fixed"

    def test_long_text_splits_by_token_count(self) -> None:
        chunker = FixedSizeChunker(ChunkConfig(strategy="fixed", chunk_size=64, overlap_ratio=0.0))
        text = "The quick brown fox jumps over the lazy dog. " * 50
        result = chunker.chunk(text, "test.md")
        assert len(result) > 1
        for chunk in result:
            assert chunk.strategy_used == "fixed"

    def test_overlap_produces_overlapping_content(self) -> None:
        chunker = FixedSizeChunker(ChunkConfig(strategy="fixed", chunk_size=64, overlap_ratio=0.2))
        text = "Word " * 200
        result = chunker.chunk(text, "test.md")
        assert len(result) > 1
        assert result[0].overlap_tokens == 0
        config = ChunkConfig(strategy="fixed", chunk_size=64, overlap_ratio=0.2)
        assert result[1].overlap_tokens == config.overlap_tokens

    def test_preview_matches_chunk(self) -> None:
        chunker = FixedSizeChunker(ChunkConfig(strategy="fixed", chunk_size=64, overlap_ratio=0.0))
        text = "Hello world. " * 50
        assert chunker.preview(text, "test.md") == chunker.chunk(text, "test.md")

    def test_stats_reports_correct_totals(self) -> None:
        chunker = FixedSizeChunker(ChunkConfig(strategy="fixed", chunk_size=64, overlap_ratio=0.0))
        text = "Hello world. " * 50
        chunks = chunker.chunk(text, "test.md")
        stats = chunker.stats(chunks)
        assert stats.total_chunks == len(chunks)
        assert stats.total_tokens > 0
        assert stats.min_chunk_size <= stats.avg_chunk_size <= stats.max_chunk_size

    def test_chunk_indices_are_sequential(self) -> None:
        chunker = FixedSizeChunker(ChunkConfig(strategy="fixed", chunk_size=64, overlap_ratio=0.0))
        text = "Some text here. " * 100
        chunks = chunker.chunk(text, "test.md")
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
