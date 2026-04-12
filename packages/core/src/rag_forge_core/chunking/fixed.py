"""Fixed-size chunking strategy.

Splits text by token count with configurable overlap.
Best for structured data and baseline comparisons.
PRD default: 512 tokens, 10-20% overlap.
"""

import tiktoken

from rag_forge_core.chunking.base import Chunk, ChunkStats, ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig

_ENCODING = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding."""
    return len(_ENCODING.encode(text))


class FixedSizeChunker(ChunkStrategy):
    """Split text into fixed-size token windows with overlap.

    Each window is exactly `chunk_size` tokens (or fewer for the last window).
    Consecutive windows share `overlap_tokens` tokens from the end of the
    previous window, giving the model context across chunk boundaries.
    """

    def __init__(self, config: ChunkConfig | None = None) -> None:
        super().__init__(config or ChunkConfig(strategy="fixed"))

    def chunk(self, text: str, source: str) -> list[Chunk]:
        """Split text into fixed-size token windows with overlap."""
        if not text.strip():
            return []

        tokens = _ENCODING.encode(text)
        chunk_size = self.config.chunk_size
        overlap = self.config.overlap_tokens
        step = max(1, chunk_size - overlap)

        chunks: list[Chunk] = []
        idx = 0
        start = 0

        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_text = _ENCODING.decode(tokens[start:end])
            chunks.append(
                Chunk(
                    text=chunk_text,
                    chunk_index=idx,
                    source_document=source,
                    strategy_used="fixed",
                    overlap_tokens=overlap if idx > 0 else 0,
                )
            )
            idx += 1
            start += step
            if end == len(tokens):
                break

        return chunks

    def preview(self, text: str, source: str) -> list[Chunk]:
        """Dry-run: show chunk boundaries without committing to storage."""
        return self.chunk(text, source)

    def stats(self, chunks: list[Chunk]) -> ChunkStats:
        """Compute statistics using tiktoken token counts."""
        if not chunks:
            return ChunkStats(
                total_chunks=0,
                avg_chunk_size=0,
                min_chunk_size=0,
                max_chunk_size=0,
                total_tokens=0,
            )

        sizes = [_token_count(c.text) for c in chunks]
        return ChunkStats(
            total_chunks=len(chunks),
            avg_chunk_size=sum(sizes) // len(sizes),
            min_chunk_size=min(sizes),
            max_chunk_size=max(sizes),
            total_tokens=sum(sizes),
        )
