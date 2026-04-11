"""End-to-end integration test: index with enrichment → query with hybrid retrieval."""

import tempfile
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.context.enricher import ContextualEnricher
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.engine import QueryEngine
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import MockReranker
from rag_forge_core.retrieval.sparse import SparseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


def _create_test_docs(tmp_path: Path) -> None:
    """Create test markdown files for indexing."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    (docs_dir / "python.md").write_text(
        "# Python\n\nPython is a versatile programming language. "
        "It is widely used for data science and machine learning. "
        "Python has a rich ecosystem of libraries including NumPy and pandas.",
        encoding="utf-8",
    )

    (docs_dir / "rust.md").write_text(
        "# Rust\n\nRust is a systems programming language focused on safety. "
        "It provides memory safety without garbage collection. "
        "Rust is commonly used for performance-critical applications.",
        encoding="utf-8",
    )

    (docs_dir / "javascript.md").write_text(
        "# JavaScript\n\nJavaScript powers interactive web applications. "
        "It runs in browsers and on servers via Node.js. "
        "TypeScript adds static typing to JavaScript.",
        encoding="utf-8",
    )


class TestHybridPipelineIntegration:
    def test_index_and_query_with_dense_only(self) -> None:
        """Baseline: index and query using dense-only retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            _create_test_docs(tmp_path)

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test",
            )
            result = pipeline.run(tmp_path / "docs")
            assert result.documents_processed == 3
            assert result.chunks_created > 0
            assert result.enrichment_summaries == 0

            retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test")
            engine = QueryEngine(retriever=retriever, generator=MockGenerator())
            query_result = engine.query("What is Python?")
            assert query_result.chunks_retrieved > 0
            assert len(query_result.answer) > 0

    def test_index_with_enrichment_and_sparse(self) -> None:
        """Index with contextual enrichment and sparse index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            _create_test_docs(tmp_path)
            sparse_path = str(tmp_path / "bm25-index")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            sparse = SparseRetriever(index_path=sparse_path)
            enricher = ContextualEnricher(generator=MockGenerator())

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test",
                enricher=enricher,
                sparse_retriever=sparse,
            )
            result = pipeline.run(tmp_path / "docs")
            assert result.documents_processed == 3
            assert result.chunks_created > 0
            assert result.enrichment_summaries == 3

            # Verify sparse index was persisted
            assert Path(sparse_path).exists()

    def test_hybrid_query_returns_results(self) -> None:
        """Full hybrid pipeline: index with enrichment → query with hybrid retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            _create_test_docs(tmp_path)
            sparse_path = str(tmp_path / "bm25-index")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            sparse = SparseRetriever(index_path=sparse_path)
            enricher = ContextualEnricher(generator=MockGenerator())

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test",
                enricher=enricher,
                sparse_retriever=sparse,
            )
            pipeline.run(tmp_path / "docs")

            # Query with hybrid retrieval
            dense = DenseRetriever(embedder=embedder, store=store, collection_name="test")
            loaded_sparse = SparseRetriever(index_path=sparse_path)
            hybrid = HybridRetriever(dense=dense, sparse=loaded_sparse, alpha=0.6)

            engine = QueryEngine(retriever=hybrid, generator=MockGenerator())
            result = engine.query("What is Python used for?")
            assert result.chunks_retrieved > 0
            assert len(result.answer) > 0

    def test_hybrid_query_with_reranker(self) -> None:
        """Full pipeline with reranker applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            _create_test_docs(tmp_path)
            sparse_path = str(tmp_path / "bm25-index")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            sparse = SparseRetriever(index_path=sparse_path)

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test",
                sparse_retriever=sparse,
            )
            pipeline.run(tmp_path / "docs")

            dense = DenseRetriever(embedder=embedder, store=store, collection_name="test")
            loaded_sparse = SparseRetriever(index_path=sparse_path)
            reranker = MockReranker()
            hybrid = HybridRetriever(
                dense=dense, sparse=loaded_sparse, alpha=0.6, reranker=reranker
            )

            engine = QueryEngine(retriever=hybrid, generator=MockGenerator())
            result = engine.query("Rust memory safety")
            assert result.chunks_retrieved > 0
