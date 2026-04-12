"""Pipeline configuration for the enterprise RAG template."""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for the enterprise RAG pipeline."""

    # Chunking
    chunk_strategy: str = "recursive"
    chunk_size: int = 512
    overlap_ratio: float = 0.1

    # Retrieval
    vector_db: str = "qdrant"
    embedding_model: str = "BAAI/bge-m3"
    retrieval_strategy: str = "hybrid"
    retrieval_alpha: float = 0.6
    top_k: int = 5

    # Reranking
    reranker: str = "cohere"
    cohere_model: str = "rerank-v3.5"
    cohere_api_key: str | None = None

    # Enrichment
    enrich: bool = True
    enrichment_model: str = "claude-sonnet-4-20250514"

    # Security
    input_guard: bool = True
    output_guard: bool = True
    faithfulness_threshold: float = 0.85
    rate_limit_per_minute: int = 60

    # Generation
    generator_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024

    # Evaluation thresholds
    context_relevance_threshold: float = 0.80
