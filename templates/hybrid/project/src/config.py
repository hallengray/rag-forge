"""Pipeline configuration for the hybrid RAG template."""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for the hybrid RAG pipeline."""

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

    # Enrichment
    enrich: bool = True
    enrichment_model: str = "claude-sonnet-4-20250514"

    # Generation
    generator_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024

    # Evaluation thresholds
    faithfulness_threshold: float = 0.85
    context_relevance_threshold: float = 0.80
