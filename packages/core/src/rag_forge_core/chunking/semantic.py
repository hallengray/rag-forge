"""Semantic chunking strategy.

Splits text at topic boundaries detected by embedding similarity.
Sentences with cosine similarity below the threshold are split into separate chunks.
PRD note: Recommended only for long-form prose; recursive is the default.
Feb 2026 benchmark: 54% accuracy vs recursive at 69% — use with care.
"""

import math
import re

import tiktoken

from rag_forge_core.chunking.base import Chunk, ChunkStats, ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.embedding.base import EmbeddingProvider

_ENCODING = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding."""
    return len(_ENCODING.encode(text))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors without numpy dependency."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using paragraph and sentence boundaries.

    Uses a simple heuristic: split on ". ", "? ", "! " when the period
    follows a lowercase letter or closing punctuation. This avoids splitting
    on common abbreviations like "Mr.", "U.S.", "e.g." where the period
    follows an uppercase letter. For production use with complex prose,
    consider a proper sentence tokenizer (NLTK, spaCy).

    Note: ``chunk_size`` and ``overlap_tokens`` from ChunkConfig are not
    enforced — merged groups can exceed chunk_size. This is by design:
    semantic chunking prioritises topic coherence over size limits.
    """
    # Normalise Windows line endings
    text = text.replace("\r\n", "\n")
    paragraphs = text.split("\n\n")
    sentences: list[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Split on sentence-ending punctuation followed by a space,
        # but only when preceded by a lowercase letter or closing quote/paren
        parts = re.split(r"(?<=[a-z.)\"\'])\. |\? |! ", para)
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences


class SemanticChunker(ChunkStrategy):
    """Split text at semantic topic boundaries using embedding similarity.

    Consecutive sentences whose embeddings have cosine similarity >= threshold
    are merged into the same chunk. When similarity drops below threshold,
    a new chunk boundary is created.
    """

    def __init__(self, config: ChunkConfig, embedder: EmbeddingProvider) -> None:
        super().__init__(config)
        self._embedder = embedder

    def chunk(self, text: str, source: str) -> list[Chunk]:
        if not text.strip():
            return []

        sentences = _split_sentences(text)
        if not sentences:
            return []

        if len(sentences) == 1:
            return [
                Chunk(
                    text=sentences[0],
                    chunk_index=0,
                    source_document=source,
                    strategy_used="semantic",
                )
            ]

        embeddings = self._embedder.embed(sentences)

        groups: list[list[str]] = [[sentences[0]]]
        for i in range(1, len(sentences)):
            sim = _cosine_similarity(embeddings[i - 1], embeddings[i])
            if sim >= self.config.cosine_threshold:
                groups[-1].append(sentences[i])
            else:
                groups.append([sentences[i]])

        return [
            Chunk(
                text=" ".join(group),
                chunk_index=idx,
                source_document=source,
                strategy_used="semantic",
            )
            for idx, group in enumerate(groups)
        ]

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
