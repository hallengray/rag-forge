"""Chunk configuration with fail-fast validation."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class ChunkConfig(BaseModel):
    """Configuration for chunking strategies. Validated at init time (fail-fast)."""

    strategy: str = Field(
        default="recursive",
        description="Chunking strategy: fixed, recursive, semantic, structural, llm-driven",
    )
    chunk_size: int = Field(
        default=512,
        ge=64,
        le=8192,
        description="Target chunk size in tokens",
    )
    overlap_ratio: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Overlap ratio between consecutive chunks (0.0 to 0.5)",
    )
    separators: list[str] = Field(
        default_factory=lambda: ["\n\n", "\n", ". ", " "],
        description="Separator hierarchy for recursive splitting",
    )
    cosine_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for semantic chunking",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> Self:
        overlap_tokens = int(self.chunk_size * self.overlap_ratio)
        if overlap_tokens >= self.chunk_size:
            msg = f"Overlap ({overlap_tokens} tokens) must be less than chunk_size ({self.chunk_size})"
            raise ValueError(msg)
        return self

    @property
    def overlap_tokens(self) -> int:
        """Calculate the overlap in tokens."""
        return int(self.chunk_size * self.overlap_ratio)
