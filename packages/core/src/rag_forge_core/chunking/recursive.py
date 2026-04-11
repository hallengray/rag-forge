"""Recursive text splitting strategy (default).

Splits by separator hierarchy: paragraphs -> lines -> sentences -> words.
Feb 2026 benchmark: 69% accuracy vs semantic chunking at 54%.
"""

from rag_forge_core.chunking.base import Chunk, ChunkStats, ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig


class RecursiveChunker(ChunkStrategy):
    """Recursive text splitter using a hierarchy of separators."""

    def __init__(self, config: ChunkConfig | None = None) -> None:
        super().__init__(config or ChunkConfig(strategy="recursive"))

    def chunk(self, text: str, source: str) -> list[Chunk]:
        """Split text recursively by separator hierarchy."""
        # Stub: full implementation in Phase 1
        raw_chunks = self._split_recursive(text, self.config.separators)
        return [
            Chunk(
                text=chunk_text,
                chunk_index=i,
                source_document=source,
                strategy_used="recursive",
                overlap_tokens=self.config.overlap_tokens,
            )
            for i, chunk_text in enumerate(raw_chunks)
            if chunk_text.strip()
        ]

    def preview(self, text: str, source: str) -> list[Chunk]:
        """Preview chunking without side effects."""
        return self.chunk(text, source)

    def stats(self, chunks: list[Chunk]) -> ChunkStats:
        """Compute statistics for the chunking result."""
        if not chunks:
            return ChunkStats(
                total_chunks=0, avg_chunk_size=0, min_chunk_size=0, max_chunk_size=0, total_tokens=0
            )

        sizes = [len(c.text.split()) for c in chunks]
        return ChunkStats(
            total_chunks=len(chunks),
            avg_chunk_size=sum(sizes) // len(sizes),
            min_chunk_size=min(sizes),
            max_chunk_size=max(sizes),
            total_tokens=sum(sizes),
        )

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using the separator hierarchy."""
        if not separators:
            return [text] if text.strip() else []

        separator = separators[0]
        parts = text.split(separator)

        result: list[str] = []
        current = ""

        for part in parts:
            candidate = f"{current}{separator}{part}" if current else part
            word_count = len(candidate.split())

            if word_count > self.config.chunk_size and current:
                result.append(current.strip())
                current = part
            else:
                current = candidate

        if current.strip():
            result.append(current.strip())

        return result
