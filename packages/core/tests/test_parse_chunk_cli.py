"""Tests for parse and chunk preview CLI commands."""

from pathlib import Path

from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker


class TestParsePreview:
    def test_parse_directory_with_files(self, tmp_path: Path) -> None:
        (tmp_path / "doc1.md").write_text("# Hello\n\nWorld")
        (tmp_path / "doc2.txt").write_text("Plain text content")
        parser = DirectoryParser()
        results, errors = parser.parse_directory(tmp_path)
        assert len(results) >= 2
        assert len(errors) == 0

    def test_parse_empty_directory(self, tmp_path: Path) -> None:
        parser = DirectoryParser()
        results, errors = parser.parse_directory(tmp_path)
        assert len(results) == 0


class TestChunkPreview:
    def test_chunk_produces_results(self, tmp_path: Path) -> None:
        (tmp_path / "doc.txt").write_text("Hello world. " * 100)
        parser = DirectoryParser()
        docs, _errors = parser.parse_directory(tmp_path)
        chunker = RecursiveChunker(ChunkConfig(chunk_size=64))
        all_chunks = []
        for doc in docs:
            all_chunks.extend(chunker.chunk(doc.text, doc.source_path))
        assert len(all_chunks) > 0
        stats = chunker.stats(all_chunks)
        assert stats.total_tokens > 0

    def test_chunk_empty_directory(self, tmp_path: Path) -> None:
        parser = DirectoryParser()
        docs, _errors = parser.parse_directory(tmp_path)
        assert len(docs) == 0
