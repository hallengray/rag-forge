"""Hybrid retriever: combines dense + sparse with Reciprocal Rank Fusion."""

from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.reranker import RerankerProtocol
from rag_forge_core.retrieval.sparse import SparseRetriever

RRF_K = 60  # Standard RRF constant


class HybridRetriever:
    """Combines dense + sparse retrieval with Reciprocal Rank Fusion (RRF).

    Alpha controls the balance: 1.0 = pure dense, 0.0 = pure sparse.
    An optional reranker post-processes the merged results.
    """

    def __init__(
        self,
        dense: DenseRetriever,
        sparse: SparseRetriever,
        alpha: float = 0.6,
        reranker: RerankerProtocol | None = None,
    ) -> None:
        self._dense = dense
        self._sparse = sparse
        self._alpha = alpha
        self._reranker = reranker

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Run both retrievers, merge via RRF, optionally rerank."""
        fetch_k = top_k * 2

        dense_results = self._dense.retrieve(query, fetch_k) if self._alpha > 0 else []
        sparse_results = self._sparse.retrieve(query, fetch_k) if self._alpha < 1 else []

        merged = self._rrf_merge(dense_results, sparse_results, top_k)

        if self._reranker is not None:
            merged = self._reranker.rerank(query, merged, top_k)

        return merged

    def _rrf_merge(
        self,
        dense_results: list[RetrievalResult],
        sparse_results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Merge dense + sparse results using Reciprocal Rank Fusion."""
        scores: dict[str, float] = {}
        result_map: dict[str, RetrievalResult] = {}

        for rank, result in enumerate(dense_results):
            rrf_score = self._alpha * (1.0 / (RRF_K + rank + 1))
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + rrf_score
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result

        for rank, result in enumerate(sparse_results):
            rrf_score = (1.0 - self._alpha) * (1.0 / (RRF_K + rank + 1))
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + rrf_score
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result

        sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)

        return [
            RetrievalResult(
                chunk_id=cid,
                text=result_map[cid].text,
                score=scores[cid],
                source_document=result_map[cid].source_document,
                metadata=result_map[cid].metadata,
            )
            for cid in sorted_ids[:top_k]
        ]

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Index chunks into the sparse index (dense indexing is separate)."""
        return self._sparse.index(chunks)
