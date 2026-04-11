"""Integration test for the full ingestion pipeline."""

from pathlib import Path

from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.ingestion.pipeline import IngestionPipeline, IngestionResult
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.storage.qdrant import QdrantStore


class TestIngestionPipeline:
    def _make_pipeline(self, collection: str = "rag-forge") -> IngestionPipeline:
        return IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(),
            embedder=MockEmbedder(),
            store=QdrantStore(),
            collection_name=collection,
        )

    def test_full_pipeline_with_markdown(self, tmp_path: Path) -> None:
        (tmp_path / "doc1.md").write_text(
            "# Introduction\n\nThis is the introduction.\n\n## Features\n\nMany great features.",
            encoding="utf-8",
        )
        (tmp_path / "doc2.txt").write_text("Plain text document.", encoding="utf-8")

        result = self._make_pipeline().run(tmp_path)

        assert isinstance(result, IngestionResult)
        assert result.documents_processed == 2
        assert result.chunks_created > 0
        assert result.chunks_indexed == result.chunks_created
        assert len(result.errors) == 0

    def test_pipeline_empty_directory(self, tmp_path: Path) -> None:
        result = self._make_pipeline().run(tmp_path)
        assert result.documents_processed == 0
        assert result.chunks_created == 0

    def test_pipeline_nonexistent_directory(self, tmp_path: Path) -> None:
        result = self._make_pipeline().run(tmp_path / "missing")
        assert result.documents_processed == 0
        assert len(result.errors) > 0

    def test_pipeline_chunks_searchable(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text(
            "Python is a programming language for data science and web development.",
            encoding="utf-8",
        )
        embedder = MockEmbedder()
        store = QdrantStore()
        pipeline = IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(),
            embedder=embedder,
            store=store,
            collection_name="search-test",
        )
        pipeline.run(tmp_path)

        query_vec = embedder.embed(["What is Python?"])[0]
        results = store.search("search-test", query_vec, top_k=3)
        assert len(results) > 0
        assert any("Python" in r.text for r in results)
