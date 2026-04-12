"""Structure-aware chunking strategy.

Respects Markdown headers (H1-H6) as chunk boundaries.
Oversized sections are sub-split using recursive token-based splitting.
Best for: technical docs, wikis, codebases.
PRD spec: Split on H1/H2/H3 boundaries.
"""

import re

import tiktoken

from rag_forge_core.chunking.base import Chunk, ChunkStats, ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker

_ENCODING = tiktoken.get_encoding("cl100k_base")
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _token_count(text: str) -> int:
    return len(_ENCODING.encode(text))


class StructuralChunker(ChunkStrategy):
    """Split text at Markdown header boundaries.

    Each header starts a new chunk. Sections that exceed chunk_size
    are sub-split using RecursiveChunker as fallback.
    """

    def __init__(self, config: ChunkConfig | None = None) -> None:
        super().__init__(config or ChunkConfig(strategy="structural"))

    def chunk(self, text: str, source: str) -> list[Chunk]:
        if not text.strip():
            return []

        sections = self._split_by_headers(text)
        if not sections:
            return [
                Chunk(
                    text=text.strip(),
                    chunk_index=0,
                    source_document=source,
                    strategy_used="structural",
                )
            ]

        chunks: list[Chunk] = []
        idx = 0
        for header_title, section_text in sections:
            section_text = section_text.strip()
            if not section_text:
                continue

            if _token_count(section_text) > self.config.chunk_size:
                sub_chunker = RecursiveChunker(self.config)
                sub_chunks = sub_chunker.chunk(section_text, source)
                for sc in sub_chunks:
                    chunks.append(
                        Chunk(
                            text=sc.text,
                            chunk_index=idx,
                            source_document=source,
                            strategy_used="structural",
                            parent_section=header_title,
                            overlap_tokens=sc.overlap_tokens,
                        )
                    )
                    idx += 1
            else:
                chunks.append(
                    Chunk(
                        text=section_text,
                        chunk_index=idx,
                        source_document=source,
                        strategy_used="structural",
                        parent_section=header_title,
                    )
                )
                idx += 1

        return chunks

    def preview(self, text: str, source: str) -> list[Chunk]:
        return self.chunk(text, source)

    def stats(self, chunks: list[Chunk]) -> ChunkStats:
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

    def _split_by_headers(self, text: str) -> list[tuple[str, str]]:
        """Split text into (header_title, section_content) pairs."""
        matches = list(_HEADER_RE.finditer(text))
        if not matches:
            return []

        sections: list[tuple[str, str]] = []

        # Content before the first header (if any)
        if matches[0].start() > 0:
            pre_content = text[: matches[0].start()].strip()
            if pre_content:
                sections.append(("(preamble)", pre_content))

        for i, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            sections.append((title, content))

        return sections
