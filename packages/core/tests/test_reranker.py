"""Tests for reranker protocol and implementations."""

from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.retrieval.reranker import MockReranker, RerankerProtocol


def _sample_results() -> list[RetrievalResult]:
    return [
        RetrievalResult(chunk_id="a", text="first", score=0.9, source_document="doc1.md"),
        RetrievalResult(chunk_id="b", text="second", score=0.8, source_document="doc2.md"),
        RetrievalResult(chunk_id="c", text="third", score=0.7, source_document="doc3.md"),
    ]


class TestMockReranker:
    def test_implements_protocol(self) -> None:
        reranker = MockReranker()
        assert isinstance(reranker, RerankerProtocol)

    def test_reverses_order(self) -> None:
        reranker = MockReranker()
        results = _sample_results()
        reranked = reranker.rerank("query", results, top_k=3)
        assert [r.chunk_id for r in reranked] == ["c", "b", "a"]

    def test_respects_top_k(self) -> None:
        reranker = MockReranker()
        results = _sample_results()
        reranked = reranker.rerank("query", results, top_k=2)
        assert len(reranked) == 2
        assert [r.chunk_id for r in reranked] == ["c", "b"]

    def test_model_name(self) -> None:
        reranker = MockReranker()
        assert reranker.model_name() == "mock-reranker"

    def test_empty_results(self) -> None:
        reranker = MockReranker()
        reranked = reranker.rerank("query", [], top_k=5)
        assert reranked == []
