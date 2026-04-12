"""Pipeline configuration for the agentic RAG template."""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    chunk_strategy: str = "recursive"
    chunk_size: int = 512
    overlap_ratio: float = 0.1
    vector_db: str = "qdrant"
    embedding_model: str = "BAAI/bge-m3"
    retrieval_strategy: str = "hybrid"
    retrieval_alpha: float = 0.6
    top_k: int = 5
    agent_mode: bool = True
    max_sub_queries: int = 5
    generator_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2048
    faithfulness_threshold: float = 0.85
    context_relevance_threshold: float = 0.80
