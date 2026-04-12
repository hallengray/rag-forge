"""Tests for structure-aware chunking strategy."""

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.structural import StructuralChunker


class TestStructuralChunker:
    def test_empty_text_returns_no_chunks(self) -> None:
        chunker = StructuralChunker(ChunkConfig(strategy="structural"))
        result = chunker.chunk("", "test.md")
        assert len(result) == 0

    def test_plain_text_returns_single_chunk(self) -> None:
        chunker = StructuralChunker(ChunkConfig(strategy="structural"))
        result = chunker.chunk("Hello world.", "test.md")
        assert len(result) == 1
        assert result[0].strategy_used == "structural"

    def test_markdown_headers_create_boundaries(self) -> None:
        chunker = StructuralChunker(ChunkConfig(strategy="structural"))
        text = "# Introduction\n\nSome intro text.\n\n## Methods\n\nSome methods.\n\n## Results\n\nSome results."
        result = chunker.chunk(text, "test.md")
        assert len(result) == 3
        assert "Introduction" in result[0].text
        assert "Methods" in result[1].text
        assert "Results" in result[2].text

    def test_parent_section_is_set(self) -> None:
        chunker = StructuralChunker(ChunkConfig(strategy="structural"))
        text = "# Title\n\nContent under title.\n\n## Section A\n\nContent A."
        result = chunker.chunk(text, "test.md")
        assert result[0].parent_section == "Title"
        assert result[1].parent_section == "Section A"

    def test_nested_headers_respected(self) -> None:
        chunker = StructuralChunker(ChunkConfig(strategy="structural"))
        text = "# Top\n\nTop content.\n\n## Sub\n\nSub content.\n\n### Deep\n\nDeep content."
        result = chunker.chunk(text, "test.md")
        assert len(result) == 3

    def test_chunk_indices_sequential(self) -> None:
        chunker = StructuralChunker(ChunkConfig(strategy="structural"))
        text = "# A\n\nA text.\n\n# B\n\nB text.\n\n# C\n\nC text."
        chunks = chunker.chunk(text, "test.md")
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_preview_matches_chunk(self) -> None:
        chunker = StructuralChunker(ChunkConfig(strategy="structural"))
        text = "# Title\n\nContent."
        assert chunker.preview(text, "test.md") == chunker.chunk(text, "test.md")

    def test_stats_reports_correct_totals(self) -> None:
        chunker = StructuralChunker(ChunkConfig(strategy="structural"))
        text = "# A\n\nContent A.\n\n# B\n\nContent B."
        chunks = chunker.chunk(text, "test.md")
        stats = chunker.stats(chunks)
        assert stats.total_chunks == len(chunks)
        assert stats.total_tokens > 0

    def test_oversized_section_gets_subsplit(self) -> None:
        """A section exceeding chunk_size should be sub-split by recursive fallback."""
        chunker = StructuralChunker(ChunkConfig(strategy="structural", chunk_size=64))
        big_section = "Word " * 200
        text = f"# Big Section\n\n{big_section}\n\n# Small\n\nTiny."
        chunks = chunker.chunk(text, "test.md")
        # Big section should be split into multiple chunks
        assert len(chunks) > 2
