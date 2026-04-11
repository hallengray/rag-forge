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
from rag_forge_core.generation.base import GenerationProvider
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


def _create_generator(provider: str) -> GenerationProvider:
    """Create a generation provider based on config string."""
    if provider == "claude":
        from rag_forge_core.generation.claude_generator import ClaudeGenerator

        return ClaudeGenerator()
    if provider == "openai":
        from rag_forge_core.generation.openai_generator import OpenAIGenerator

        return OpenAIGenerator()
    from rag_forge_core.generation.mock_generator import MockGenerator

    return MockGenerator()


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


def cmd_query(args: argparse.Namespace) -> None:
    """Run the query command."""
    config = json.loads(args.config_json) if args.config_json else {}
    embedding_provider = args.embedding or config.get("embedding_provider", "mock")
    generator_provider = args.generator or config.get("generator_provider", "mock")
    collection = args.collection or config.get("collection_name", "rag-forge")
    top_k = int(args.top_k)

    from rag_forge_core.query.engine import QueryEngine

    engine = QueryEngine(
        embedder=_create_embedder(embedding_provider),
        store=QdrantStore(),
        generator=_create_generator(generator_provider),
        collection_name=collection,
        top_k=top_k,
    )
    result = engine.query(args.question)
    output = {
        "answer": result.answer,
        "model_used": result.model_used,
        "chunks_retrieved": result.chunks_retrieved,
        "sources": [
            {"text": s.text[:200], "score": s.score, "id": s.id}
            for s in result.sources
        ],
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

    query_parser = subparsers.add_parser("query", help="Query the RAG pipeline")
    query_parser.add_argument("--question", required=True, help="The question to ask")
    query_parser.add_argument("--embedding", help="Embedding provider: openai | local | mock")
    query_parser.add_argument("--generator", help="Generation provider: claude | openai | mock")
    query_parser.add_argument("--collection", help="Collection name")
    query_parser.add_argument("--top-k", default="5", help="Number of chunks to retrieve")
    query_parser.add_argument("--config-json", help="JSON config from TS CLI")

    args = parser.parse_args()
    if args.command == "index":
        cmd_index(args)
    elif args.command == "query":
        cmd_query(args)


if __name__ == "__main__":
    main()
