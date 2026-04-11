"""Python CLI entry point for the rag-forge TypeScript bridge.

Called via: uv run python -m rag_forge_core.cli index --source ./docs --config-json '{...}'
Outputs JSON to stdout for the TypeScript CLI to parse and display.
"""

import argparse
import json
import sys
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.storage.qdrant import QdrantStore


def _create_embedder(provider: str) -> EmbeddingProvider:
    """Create an embedding provider based on config string."""
    if provider == "openai":
        from rag_forge_core.embedding.openai_embedder import OpenAIEmbedder

        return OpenAIEmbedder()
    if provider == "local":
        from rag_forge_core.embedding.local_embedder import LocalEmbedder

        return LocalEmbedder()
    return MockEmbedder()


def cmd_index(args: argparse.Namespace) -> None:
    """Run the index command."""
    config = json.loads(args.config_json) if args.config_json else {}

    source = Path(args.source)
    collection = args.collection or config.get("collection_name", "rag-forge")
    embedding_provider = args.embedding or config.get("embedding_provider", "mock")
    chunk_size = config.get("chunk_size", 512)
    overlap_ratio = config.get("overlap_ratio", 0.1)

    chunk_config = ChunkConfig(
        strategy="recursive",
        chunk_size=chunk_size,
        overlap_ratio=overlap_ratio,
    )

    pipeline = IngestionPipeline(
        parser=DirectoryParser(),
        chunker=RecursiveChunker(chunk_config),
        embedder=_create_embedder(embedding_provider),
        store=QdrantStore(),
        collection_name=collection,
    )

    result = pipeline.run(source)

    output = {
        "success": len(result.errors) == 0,
        "documents_processed": result.documents_processed,
        "chunks_created": result.chunks_created,
        "chunks_indexed": result.chunks_indexed,
        "errors": result.errors,
    }
    json.dump(output, sys.stdout)


def main() -> None:
    """Main entry point for the Python CLI bridge."""
    parser = argparse.ArgumentParser(prog="rag-forge-core")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index documents")
    index_parser.add_argument("--source", required=True, help="Source directory")
    index_parser.add_argument("--collection", help="Collection name")
    index_parser.add_argument("--embedding", help="Provider: openai | local | mock")
    index_parser.add_argument("--config-json", help="JSON config from TS CLI")

    args = parser.parse_args()
    if args.command == "index":
        cmd_index(args)


if __name__ == "__main__":
    main()
