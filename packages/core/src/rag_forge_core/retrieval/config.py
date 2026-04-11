"""Retrieval configuration with Pydantic validation (fail-fast)."""

from enum import StrEnum

from pydantic import BaseModel, Field


class RetrievalStrategy(StrEnum):
    """Available retrieval strategies."""

    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


class RerankerType(StrEnum):
    """Available reranker implementations."""

    NONE = "none"
    COHERE = "cohere"
    BGE_LOCAL = "bge-local"


class RetrievalConfig(BaseModel):
    """Validated retrieval configuration.

    Validates at init time (fail-fast pattern, consistent with ChunkConfig).
    """

    strategy: RetrievalStrategy = RetrievalStrategy.DENSE
    alpha: float = Field(default=0.6, ge=0.0, le=1.0)
    top_k: int = Field(default=5, ge=1, le=100)
    sparse_index_path: str | None = None
    reranker: RerankerType = RerankerType.NONE
    cohere_model: str = "rerank-v3.5"
    cohere_api_key: str | None = None
    bge_model_name: str = "BAAI/bge-reranker-v2-m3"
