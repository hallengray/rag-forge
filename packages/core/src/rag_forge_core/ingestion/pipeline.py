"""Full ingestion pipeline: parse -> chunk -> embed -> store."""

from dataclasses import dataclass
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig


@dataclass
class IngestionResult:
    """Result of an ingestion pipeline run."""

    documents_processed: int
    chunks_created: int
    chunks_indexed: int
    errors: list[str]


class IngestionPipeline:
    """Orchestrates the full document ingestion process.

    Pipeline stages:
    1. Parse: Extract text from documents (PDF, MD, HTML, etc.)
    2. Chunk: Split documents using the configured strategy
    3. Embed: Generate vector embeddings for each chunk
    4. Store: Index chunks in the vector database
    """

    def __init__(self, chunk_config: ChunkConfig | None = None) -> None:
        self.chunk_config = chunk_config or ChunkConfig()

    def run(self, source_path: str | Path) -> IngestionResult:
        """Run the full ingestion pipeline on a directory of documents."""
        # Stub: full implementation in Phase 1
        _ = source_path
        return IngestionResult(
            documents_processed=0,
            chunks_created=0,
            chunks_indexed=0,
            errors=["Ingestion pipeline not yet implemented"],
        )
