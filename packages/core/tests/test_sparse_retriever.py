"""Tests for the BM25 sparse retriever."""

import tempfile
from pathlib import Path

from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.sparse import SparseRetriever


def _sample_chunks() -> list[dict[str, str]]:
    """Create a small corpus for testing."""
    return [
        {"id": "chunk-0", "text": "Python is a popular programming language"},
        {"id": "chunk-1", "text": "JavaScript runs in the browser"},
        {"id": "chunk-2", "text": "Rust provides memory safety without garbage collection"},
        {"id": "chunk-3", "text": "Python supports machine learning with libraries like PyTorch"},
        {"id": "chunk-4", "text": "TypeScript adds static types to JavaScript"},
    ]


class TestSparseRetriever:
    def test_implements_protocol(self) -> None:
        retriever = SparseRetriever()
        assert isinstance(retriever, RetrieverProtocol)

    def test_index_returns_count(self) -> None:
        retriever = SparseRetriever()
        count = retriever.index(_sample_chunks())
        assert count == 5

    def test_retrieve_returns_results(self) -> None:
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("Python programming", top_k=2)
        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_retrieve_result_fields(self) -> None:
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("Python", top_k=1)
        result = results[0]
        assert isinstance(result.chunk_id, str)
        assert isinstance(result.text, str)
        assert isinstance(result.score, float)
        assert result.score > 0.0

    def test_retrieve_keyword_relevance(self) -> None:
        """BM25 should rank documents containing the query terms higher."""
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("JavaScript browser", top_k=2)
        result_texts = [r.text for r in results]
        assert any("JavaScript" in t for t in result_texts)

    def test_retrieve_empty_index(self) -> None:
        retriever = SparseRetriever()
        results = retriever.retrieve("anything", top_k=5)
        assert results == []

    def test_retrieve_respects_top_k(self) -> None:
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("Python", top_k=1)
        assert len(results) == 1

    def test_top_k_larger_than_corpus(self) -> None:
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("Python", top_k=100)
        assert len(results) == 5


class TestSparseRetrieverPersistence:
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "bm25-index")
            retriever = SparseRetriever(index_path=index_path)
            retriever.index(_sample_chunks())
            retriever.save()

            loaded = SparseRetriever(index_path=index_path)
            loaded.load()
            results = loaded.retrieve("Python", top_k=2)
            assert len(results) == 2

    def test_auto_save_on_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "bm25-index")
            retriever = SparseRetriever(index_path=index_path)
            retriever.index(_sample_chunks())

            loaded = SparseRetriever(index_path=index_path)
            loaded.load()
            results = loaded.retrieve("Python", top_k=1)
            assert len(results) == 1

    def test_auto_load_on_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "bm25-index")
            retriever = SparseRetriever(index_path=index_path)
            retriever.index(_sample_chunks())

            auto_loaded = SparseRetriever(index_path=index_path)
            results = auto_loaded.retrieve("JavaScript", top_k=1)
            assert len(results) == 1
