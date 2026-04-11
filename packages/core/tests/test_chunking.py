"""Smoke tests for the chunking module."""

import pytest

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker


class TestChunkConfig:
    def test_default_config(self) -> None:
        config = ChunkConfig()
        assert config.strategy == "recursive"
        assert config.chunk_size == 512
        assert config.overlap_ratio == 0.1

    def test_overlap_tokens_calculation(self) -> None:
        config = ChunkConfig(chunk_size=512, overlap_ratio=0.2)
        assert config.overlap_tokens == 102

    def test_invalid_overlap_ratio(self) -> None:
        with pytest.raises(ValueError):
            ChunkConfig(chunk_size=100, overlap_ratio=1.5)

    def test_chunk_size_bounds(self) -> None:
        with pytest.raises(ValueError):
            ChunkConfig(chunk_size=10)
        with pytest.raises(ValueError):
            ChunkConfig(chunk_size=10000)


class TestRecursiveChunker:
    def test_empty_text(self) -> None:
        chunker = RecursiveChunker()
        result = chunker.chunk("", "test.md")
        assert len(result) == 0

    def test_simple_text(self) -> None:
        chunker = RecursiveChunker()
        text = "Hello world. This is a test document."
        result = chunker.chunk(text, "test.md")
        assert len(result) > 0
        assert result[0].source_document == "test.md"
        assert result[0].strategy_used == "recursive"

    def test_stats_empty(self) -> None:
        chunker = RecursiveChunker()
        stats = chunker.stats([])
        assert stats.total_chunks == 0
