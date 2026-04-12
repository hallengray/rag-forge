"""Full ingestion pipeline: parse -> chunk -> [enrich] -> embed -> store [+ sparse index]."""

import uuid
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opentelemetry import trace

from rag_forge_core.chunking.base import Chunk, ChunkStrategy
from rag_forge_core.context.enricher import ContextualEnricher
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.retrieval.sparse import SparseRetriever
from rag_forge_core.storage.base import VectorItem, VectorStore

EMBEDDING_BATCH_SIZE = 2048


@dataclass
class IngestionResult:
    """Result of an ingestion pipeline run."""

    documents_processed: int
    chunks_created: int
    chunks_indexed: int
    enrichment_summaries: int = 0
    errors: list[str] = field(default_factory=list)


class IngestionPipeline:
    """Orchestrates the full document ingestion process.

    Pipeline stages:
    1. Parse: Extract text from documents
    2. Chunk: Split documents using the configured strategy
    3. Enrich (optional): Prepend document summaries to chunks
    4. Embed: Generate vector embeddings for each chunk
    5. Store: Index chunks in the vector database
    6. Sparse Index (optional): Build BM25 index for sparse retrieval
    """

    def __init__(
        self,
        parser: DirectoryParser,
        chunker: ChunkStrategy,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection_name: str = "rag-forge",
        enricher: ContextualEnricher | None = None,
        sparse_retriever: SparseRetriever | None = None,
        tracer: trace.Tracer | None = None,
    ) -> None:
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.store = store
        self.collection_name = collection_name
        self.enricher = enricher
        self.sparse_retriever = sparse_retriever
        self._tracer = tracer

    def _span(self, name: str) -> Any:
        """Return an active span context manager, or a no-op if no tracer is configured."""
        if self._tracer is not None:
            return self._tracer.start_as_current_span(name)
        return nullcontext()

    def run(self, source_path: str | Path) -> IngestionResult:
        """Run the full ingestion pipeline on a directory of documents."""
        with self._span("rag-forge.ingest"):
            source = Path(source_path)
            errors: list[str] = []
            enrichment_summaries = 0

            # 1. Parse documents
            with self._span("rag-forge.parse") as span:
                documents, parse_errors = self.parser.parse_directory(source)
                errors.extend(parse_errors)
                if span is not None:
                    span.set_attribute("document_count", len(documents))
                    span.set_attribute("error_count", len(parse_errors))

            if not documents:
                return IngestionResult(
                    documents_processed=0, chunks_created=0, chunks_indexed=0, errors=errors
                )

            # 2. Chunk documents (and optionally enrich per document)
            all_chunks: list[Chunk] = []
            with self._span("rag-forge.chunk") as span:
                for doc in documents:
                    chunks = self.chunker.chunk(doc.text, doc.source_path)
                    all_chunks.extend(chunks)
                strategy = all_chunks[0].strategy_used if all_chunks else "unknown"
                if span is not None:
                    span.set_attribute("chunk_count", len(all_chunks))
                    span.set_attribute("strategy", strategy)

            # 3. Enrich (optional): prepend document summary to each chunk
            if self.enricher is not None and all_chunks:
                with self._span("rag-forge.enrich") as span:
                    enriched: list[Chunk] = []
                    for doc in documents:
                        doc_chunks = [c for c in all_chunks if c.source_document == doc.source_path]
                        if doc_chunks:
                            doc_chunks = self.enricher.enrich(doc, doc_chunks)
                            enrichment_summaries += 1
                        enriched.extend(doc_chunks)
                    all_chunks = enriched
                    if span is not None:
                        span.set_attribute("summaries_generated", enrichment_summaries)

            if not all_chunks:
                return IngestionResult(
                    documents_processed=len(documents),
                    chunks_created=0,
                    chunks_indexed=0,
                    enrichment_summaries=enrichment_summaries,
                    errors=errors,
                )

            # 4. Embed chunks in batches
            chunk_texts = [c.text for c in all_chunks]
            all_vectors: list[list[float]] = []
            with self._span("rag-forge.embed") as span:
                batch_count = 0
                for i in range(0, len(chunk_texts), EMBEDDING_BATCH_SIZE):
                    batch = chunk_texts[i : i + EMBEDDING_BATCH_SIZE]
                    vectors = self.embedder.embed(batch)
                    all_vectors.extend(vectors)
                    batch_count += 1
                if span is not None:
                    span.set_attribute("chunk_count", len(all_chunks))
                    span.set_attribute("model", self.embedder.__class__.__name__)
                    span.set_attribute("batch_count", batch_count)

            # 5. Create collection and upsert to vector store
            items = [
                VectorItem(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    text=chunk.text,
                    metadata={
                        "source_document": chunk.source_document,
                        "chunk_index": chunk.chunk_index,
                        "strategy": chunk.strategy_used,
                    },
                )
                for chunk, vector in zip(all_chunks, all_vectors, strict=True)
            ]

            with self._span("rag-forge.store") as span:
                self.store.create_collection(self.collection_name, self.embedder.dimension())
                indexed_count = self.store.upsert(self.collection_name, items)
                if span is not None:
                    span.set_attribute("chunks_indexed", indexed_count)
                    span.set_attribute("collection", self.collection_name)

            # 6. Sparse index (optional): build BM25 index
            if self.sparse_retriever is not None:
                with self._span("rag-forge.sparse_index") as span:
                    sparse_chunks = [
                        {
                            "id": item.id,
                            "text": item.text,
                            "source_document": str(item.metadata.get("source_document", "")),
                        }
                        for item in items
                    ]
                    self.sparse_retriever.index(sparse_chunks)
                    if span is not None:
                        span.set_attribute("chunk_count", len(sparse_chunks))

            return IngestionResult(
                documents_processed=len(documents),
                chunks_created=len(all_chunks),
                chunks_indexed=indexed_count,
                enrichment_summaries=enrichment_summaries,
                errors=errors,
            )
