"""Retrieval engine: dense, sparse, hybrid, and reranking."""

from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.config import RerankerType, RetrievalConfig, RetrievalStrategy
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import (
    BGELocalReranker,
    CohereReranker,
    MockReranker,
    RerankerProtocol,
)
from rag_forge_core.retrieval.sparse import SparseRetriever

__all__ = [
    "BGELocalReranker",
    "CohereReranker",
    "DenseRetriever",
    "HybridRetriever",
    "MockReranker",
    "RerankerProtocol",
    "RerankerType",
    "RetrievalConfig",
    "RetrievalResult",
    "RetrievalStrategy",
    "RetrieverProtocol",
    "SparseRetriever",
]
