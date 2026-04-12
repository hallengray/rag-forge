"""LLM-driven chunking strategy.

Uses a small LLM to identify meaningful boundary points in text.
The LLM receives numbered sentences and returns boundary indices as JSON.
Falls back to size-based splitting when the LLM response is unparseable.
PRD recommendation: Claude Haiku / GPT-4o-mini for cost efficiency.
"""

import json
import logging

import tiktoken

from rag_forge_core.chunking.base import Chunk, ChunkStats, ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.generation.base import GenerationProvider

_ENCODING = tiktoken.get_encoding("cl100k_base")
_LOG = logging.getLogger(__name__)

_BOUNDARY_PROMPT = """You are a document chunking assistant. Given the following numbered sentences, identify the indices where topic boundaries occur. A boundary means the content shifts to a different topic or subtopic.

Return a JSON array of sentence indices (0-based) where splits should happen. For example: [3, 7, 12] means split BEFORE sentences 3, 7, and 12.

If there are no clear boundaries, return an empty array: []

Sentences:
{sentences}"""


def _token_count(text: str) -> int:
    return len(_ENCODING.encode(text))


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences for LLM analysis."""
    # Normalise Windows line endings
    text = text.replace("\r\n", "\n")
    paragraphs = text.split("\n\n")
    sentences: list[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        parts = para.replace(". ", ".\n").replace("? ", "?\n").replace("! ", "!\n").split("\n")
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences


class LLMDrivenChunker(ChunkStrategy):
    """Use an LLM to identify semantic boundaries in text.

    Sends numbered sentences to the LLM and asks for boundary indices.
    Falls back to size-based splitting on LLM failure or invalid response.
    """

    def __init__(self, config: ChunkConfig, generator: GenerationProvider) -> None:
        super().__init__(config)
        self._generator = generator

    def chunk(self, text: str, source: str) -> list[Chunk]:
        if not text.strip():
            return []

        sentences = _split_into_sentences(text)
        if not sentences:
            return []

        if len(sentences) == 1:
            return [
                Chunk(
                    text=sentences[0],
                    chunk_index=0,
                    source_document=source,
                    strategy_used="llm-driven",
                )
            ]

        boundaries = self._get_boundaries(sentences)
        groups = self._apply_boundaries(sentences, boundaries)

        return [
            Chunk(
                text=" ".join(group),
                chunk_index=idx,
                source_document=source,
                strategy_used="llm-driven",
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

    def _get_boundaries(self, sentences: list[str]) -> list[int]:
        """Ask the LLM for boundary indices. Returns sorted list of split points."""
        numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(sentences))
        prompt = _BOUNDARY_PROMPT.format(sentences=numbered)

        try:
            response = self._generator.generate(
                system_prompt="You are a document analysis assistant. Respond only with valid JSON.",
                user_prompt=prompt,
            )
            boundaries = json.loads(response)
            if not isinstance(boundaries, list):
                _LOG.warning(
                    "LLM returned non-list: %s, falling back to size-based splitting",
                    type(boundaries),
                )
                return self._fallback_boundaries(sentences)
            # Empty list from LLM means "no boundaries" — return as-is (single group)
            if len(boundaries) == 0:
                return []
            valid = sorted({int(b) for b in boundaries if 0 < int(b) < len(sentences)})
            return valid if valid else self._fallback_boundaries(sentences)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            _LOG.warning("LLM boundary parsing failed: %s, falling back", e)
            return self._fallback_boundaries(sentences)

    def _fallback_boundaries(self, sentences: list[str]) -> list[int]:
        """Size-based fallback: split every chunk_size tokens."""
        boundaries: list[int] = []
        current_tokens = 0
        for i, sentence in enumerate(sentences):
            current_tokens += _token_count(sentence)
            if current_tokens >= self.config.chunk_size and i > 0:
                boundaries.append(i)
                current_tokens = _token_count(sentence)
        return boundaries

    def _apply_boundaries(self, sentences: list[str], boundaries: list[int]) -> list[list[str]]:
        """Split sentences into groups at the given boundary indices."""
        if not boundaries:
            return [sentences]
        groups: list[list[str]] = []
        prev = 0
        for boundary in boundaries:
            groups.append(sentences[prev:boundary])
            prev = boundary
        groups.append(sentences[prev:])
        return [g for g in groups if g]
