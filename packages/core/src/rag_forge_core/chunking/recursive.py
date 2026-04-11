"""Recursive text splitting strategy (default).

Splits by separator hierarchy: paragraphs -> lines -> sentences -> words.
Feb 2026 benchmark: 69% accuracy vs semantic chunking at 54%.
"""

import tiktoken

from rag_forge_core.chunking.base import Chunk, ChunkStats, ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig

_ENCODING = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding."""
    return len(_ENCODING.encode(text))


class RecursiveChunker(ChunkStrategy):
    """Recursive text splitter using a hierarchy of separators with tiktoken token counting."""

    def __init__(self, config: ChunkConfig | None = None) -> None:
        super().__init__(config or ChunkConfig(strategy="recursive"))

    def chunk(self, text: str, source: str) -> list[Chunk]:
        """Split text recursively by separator hierarchy with overlap."""
        raw_chunks = self._split_recursive(text, self.config.separators)
        raw_chunks = [c for c in raw_chunks if c.strip()]

        if not raw_chunks:
            return []

        chunks_with_overlap = self._apply_overlap(raw_chunks)

        return [
            Chunk(
                text=chunk_text,
                chunk_index=i,
                source_document=source,
                strategy_used="recursive",
                overlap_tokens=self.config.overlap_tokens if i > 0 else 0,
            )
            for i, chunk_text in enumerate(chunks_with_overlap)
        ]

    def preview(self, text: str, source: str) -> list[Chunk]:
        """Preview chunking without side effects."""
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

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """Add overlap tokens from the end of each chunk to the start of the next."""
        overlap_tokens = self.config.overlap_tokens
        if overlap_tokens <= 0 or len(chunks) <= 1:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tokens = _ENCODING.encode(chunks[i - 1])
            overlap_text = _ENCODING.decode(prev_tokens[-overlap_tokens:])
            result.append(overlap_text + " " + chunks[i])

        return result

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using the separator hierarchy with tiktoken sizing.

        For each separator level, accumulate parts until the token budget is
        reached.  Any piece that still exceeds the budget is recursed into with
        the remaining separators so we always drill down to finer splits.
        """
        if not separators:
            return [text] if text.strip() else []

        separator = separators[0]
        remaining_separators = separators[1:]
        parts = text.split(separator)

        result: list[str] = []
        current = ""

        for part in parts:
            candidate = f"{current}{separator}{part}" if current else part
            token_count = _token_count(candidate)

            if token_count > self.config.chunk_size and current:
                # Flush current accumulation, then decide what to do with part
                result.append(current.strip())
                # If the single part itself exceeds the budget, recurse deeper
                if _token_count(part) > self.config.chunk_size and remaining_separators:
                    result.extend(self._split_recursive(part, remaining_separators))
                    current = ""
                else:
                    current = part
            elif token_count > self.config.chunk_size and not current:
                # Single part already exceeds budget — recurse immediately
                if remaining_separators:
                    result.extend(self._split_recursive(part, remaining_separators))
                else:
                    result.append(part.strip())
                current = ""
            else:
                current = candidate

        if current.strip():
            result.append(current.strip())

        return result
