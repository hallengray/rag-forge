"""Contextual enrichment: prepend document summaries to chunks before embedding.

Implements the Anthropic contextual retrieval technique. A short summary of the
entire document is generated via an LLM, then prepended to each chunk's text.
This gives the embedding model document-level context, improving retrieval
accuracy by 2-18% (per Anthropic research).
"""

import logging
from dataclasses import dataclass

from rag_forge_core.chunking.base import Chunk
from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.parsing.base import Document

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM_PROMPT = (
    "You are a document summarizer. Generate a concise 2-3 sentence summary "
    "of the following document. Focus on the main topic, key entities, and the "
    "document's purpose. This summary will be prepended to individual chunks to "
    "provide context for embedding."
)


@dataclass
class EnrichmentResult:
    """Result of contextual enrichment for a single document."""

    document_source: str
    summary: str
    chunks_enriched: int


class ContextualEnricher:
    """Prepends document-level summaries to chunks before embedding."""

    def __init__(
        self,
        generator: GenerationProvider,
        max_document_tokens: int = 8000,
    ) -> None:
        self._generator = generator
        self._max_document_tokens = max_document_tokens

    def enrich(self, document: Document, chunks: list[Chunk]) -> list[Chunk]:
        """Generate a document summary and prepend it to each chunk.

        Returns new Chunk objects with enriched text. Original text is
        preserved in chunk.metadata["original_text"]. The summary is
        stored in chunk.metadata["document_summary"].
        """
        if not chunks:
            return []

        try:
            summary = self._generate_summary(document)
        except Exception:
            logger.warning(
                "Enrichment failed for %s, returning original chunks",
                document.source_path,
                exc_info=True,
            )
            return list(chunks)

        enriched: list[Chunk] = []
        for chunk in chunks:
            original_metadata = dict(chunk.metadata) if chunk.metadata else {}
            original_metadata["original_text"] = chunk.text
            original_metadata["document_summary"] = summary

            enriched.append(
                Chunk(
                    text=f"[Document context: {summary}]\n\n{chunk.text}",
                    chunk_index=chunk.chunk_index,
                    source_document=chunk.source_document,
                    strategy_used=chunk.strategy_used,
                    parent_section=chunk.parent_section,
                    overlap_tokens=chunk.overlap_tokens,
                    metadata=original_metadata,
                )
            )

        return enriched

    def _generate_summary(self, document: Document) -> str:
        """Generate a concise summary of the document for contextual enrichment."""
        doc_text = document.text
        # Rough truncation: ~4 chars per token on average
        char_limit = self._max_document_tokens * 4
        if len(doc_text) > char_limit:
            doc_text = doc_text[:char_limit]

        return self._generator.generate(_SUMMARY_SYSTEM_PROMPT, doc_text)
