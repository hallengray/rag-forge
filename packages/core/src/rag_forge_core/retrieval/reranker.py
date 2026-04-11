"""Reranker protocol and implementations for post-retrieval re-scoring."""

import logging
from typing import Protocol, runtime_checkable

from rag_forge_core.retrieval.base import RetrievalResult

logger = logging.getLogger(__name__)


@runtime_checkable
class RerankerProtocol(Protocol):
    """Protocol for all reranker implementations."""

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]: ...

    def model_name(self) -> str: ...


class CohereReranker:
    """Reranker using the Cohere Rerank API.

    Requires the `cohere` package: pip install rag-forge-core[cohere]
    """

    def __init__(self, api_key: str, model: str = "rerank-v3.5") -> None:
        import cohere

        self._client = cohere.Client(api_key)
        self._model = model

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Call Cohere Rerank API, update scores, re-sort."""
        if top_k <= 0:
            return []
        if not results:
            return []

        try:
            response = self._client.rerank(
                query=query,
                documents=[r.text for r in results],
                top_n=min(top_k, len(results)),
                model=self._model,
            )

            reranked: list[RetrievalResult] = []
            for item in response.results:
                original = results[item.index]
                reranked.append(
                    RetrievalResult(
                        chunk_id=original.chunk_id,
                        text=original.text,
                        score=item.relevance_score,
                        source_document=original.source_document,
                        metadata={**original.metadata, "reranker": self._model},
                    )
                )
            return reranked
        except Exception:
            logger.warning("Cohere reranking failed, returning original results", exc_info=True)
            return results[:top_k]

    def model_name(self) -> str:
        return self._model


class BGELocalReranker:
    """Local cross-encoder reranker using BAAI/bge-reranker-v2-m3.

    Requires sentence-transformers: pip install rag-forge-core[local]
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        from sentence_transformers import CrossEncoder

        self._model_name = model_name
        self._model = CrossEncoder(model_name)

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Score each (query, chunk) pair with cross-encoder, re-sort."""
        if top_k <= 0:
            return []
        if not results:
            return []

        try:
            pairs = [[query, r.text] for r in results]
            scores = self._model.predict(pairs)

            scored = list(zip(results, scores, strict=True))
            scored.sort(key=lambda x: float(x[1]), reverse=True)

            return [
                RetrievalResult(
                    chunk_id=r.chunk_id,
                    text=r.text,
                    score=float(s),
                    source_document=r.source_document,
                    metadata={**r.metadata, "reranker": self._model_name},
                )
                for r, s in scored[:top_k]
            ]
        except Exception:
            logger.warning("BGE local reranking failed, returning original results", exc_info=True)
            return results[:top_k]

    def model_name(self) -> str:
        return self._model_name


class MockReranker:
    """Deterministic reranker for testing. Reverses result order."""

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Reverse the input order (deterministic, predictable in tests)."""
        if top_k <= 0:
            return []
        _ = query
        return list(reversed(results))[:top_k]

    def model_name(self) -> str:
        return "mock-reranker"
