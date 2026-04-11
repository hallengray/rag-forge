"""Full ingestion pipeline: parse -> chunk -> embed -> store."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from rag_forge_core.chunking.base import ChunkStrategy
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.storage.base import VectorItem, VectorStore

EMBEDDING_BATCH_SIZE = 2048


@dataclass
class IngestionResult:
    """Result of an ingestion pipeline run."""

    documents_processed: int
    chunks_created: int
    chunks_indexed: int
    errors: list[str] = field(default_factory=list)


class IngestionPipeline:
    """Orchestrates the full document ingestion process.

    Pipeline stages:
    1. Parse: Extract text from documents
    2. Chunk: Split documents using the configured strategy
    3. Embed: Generate vector embeddings for each chunk
    4. Store: Index chunks in the vector database
    """

    def __init__(
        self,
        parser: DirectoryParser,
        chunker: ChunkStrategy,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection_name: str = "rag-forge",
    ) -> None:
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.store = store
        self.collection_name = collection_name

    def run(self, source_path: str | Path) -> IngestionResult:
        """Run the full ingestion pipeline on a directory of documents."""
        source = Path(source_path)
        errors: list[str] = []

        # 1. Parse documents
        documents, parse_errors = self.parser.parse_directory(source)
        errors.extend(parse_errors)

        if not documents:
            return IngestionResult(
                documents_processed=0, chunks_created=0, chunks_indexed=0, errors=errors
            )

        # 2. Chunk documents
        all_chunks = []
        for doc in documents:
            chunks = self.chunker.chunk(doc.text, doc.source_path)
            all_chunks.extend(chunks)

        if not all_chunks:
            return IngestionResult(
                documents_processed=len(documents),
                chunks_created=0,
                chunks_indexed=0,
                errors=errors,
            )

        # 3. Embed chunks in batches
        chunk_texts = [c.text for c in all_chunks]
        all_vectors: list[list[float]] = []
        for i in range(0, len(chunk_texts), EMBEDDING_BATCH_SIZE):
            batch = chunk_texts[i : i + EMBEDDING_BATCH_SIZE]
            vectors = self.embedder.embed(batch)
            all_vectors.extend(vectors)

        # 4. Create collection and upsert
        self.store.create_collection(self.collection_name, self.embedder.dimension())

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
        indexed_count = self.store.upsert(self.collection_name, items)

        return IngestionResult(
            documents_processed=len(documents),
            chunks_created=len(all_chunks),
            chunks_indexed=indexed_count,
            errors=errors,
        )
