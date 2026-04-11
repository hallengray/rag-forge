"""Abstract base class for all chunking strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from rag_forge_core.chunking.config import ChunkConfig


@dataclass
class Chunk:
    """A single chunk of text with metadata."""

    text: str
    chunk_index: int
    source_document: str
    strategy_used: str
    parent_section: str | None = None
    overlap_tokens: int = 0
    metadata: dict[str, str | int | float] | None = None


@dataclass
class ChunkStats:
    """Statistics about a chunking operation."""

    total_chunks: int
    avg_chunk_size: int
    min_chunk_size: int
    max_chunk_size: int
    total_tokens: int


class ChunkStrategy(ABC):
    """Abstract base class that all chunking strategies must implement.

    Ensures strategies are interchangeable and the evaluation engine
    can compare performance across strategies on the same dataset.
    """

    def __init__(self, config: ChunkConfig) -> None:
        self.config = config

    @abstractmethod
    def chunk(self, text: str, source: str) -> list[Chunk]:
        """Split text into chunks according to the strategy."""

    @abstractmethod
    def preview(self, text: str, source: str) -> list[Chunk]:
        """Dry-run: show chunk boundaries without committing to storage."""

    @abstractmethod
    def stats(self, chunks: list[Chunk]) -> ChunkStats:
        """Compute statistics about the chunking result."""
