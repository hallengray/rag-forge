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
from rag_forge_core.context.enricher import ContextualEnricher
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import RerankerProtocol
from rag_forge_core.retrieval.sparse import SparseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


def _create_embedder(provider: str) -> EmbeddingProvider:
    """Create an embedding provider based on config string."""
    if provider == "openai":
        from rag_forge_core.embedding.openai_embedder import OpenAIEmbedder

        return OpenAIEmbedder()
    if provider == "local":
        from rag_forge_core.embedding.local_embedder import LocalEmbedder

        return LocalEmbedder()
    if provider == "mock":
        return MockEmbedder()
    raise ValueError(
        f"Unknown embedding provider: {provider!r}. "
        "Expected one of: 'openai', 'local', 'mock'."
    )


def _create_generator(provider: str) -> GenerationProvider:
    """Create a generation provider based on config string."""
    if provider == "claude":
        from rag_forge_core.generation.claude_generator import ClaudeGenerator

        return ClaudeGenerator()
    if provider == "openai":
        from rag_forge_core.generation.openai_generator import OpenAIGenerator

        return OpenAIGenerator()
    if provider == "mock":
        from rag_forge_core.generation.mock_generator import MockGenerator

        return MockGenerator()
    raise ValueError(
        f"Unknown generation provider: {provider!r}. "
        "Expected one of: 'mock', 'claude', 'openai'."
    )


def _create_reranker(reranker_type: str, cohere_api_key: str | None = None) -> RerankerProtocol | None:
    """Create a reranker based on config string."""
    if reranker_type == "none":
        return None
    if reranker_type == "cohere":
        from rag_forge_core.retrieval.reranker import CohereReranker

        if not cohere_api_key:
            raise ValueError("Cohere reranker requires COHERE_API_KEY")
        return CohereReranker(api_key=cohere_api_key)
    if reranker_type == "bge-local":
        from rag_forge_core.retrieval.reranker import BGELocalReranker

        return BGELocalReranker()
    raise ValueError(
        f"Unknown reranker: {reranker_type!r}. "
        "Expected one of: 'none', 'cohere', 'bge-local'."
    )


def cmd_index(args: argparse.Namespace) -> None:
    """Run the index command."""
    try:
        config = json.loads(args.config_json) if args.config_json else {}
    except json.JSONDecodeError as e:
        json.dump({"success": False, "errors": [f"Invalid --config-json: {e}"]}, sys.stdout)
        sys.exit(1)

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

    # Optional enricher
    enricher = None
    if args.enrich:
        enrichment_gen = args.enrichment_generator or embedding_provider
        gen_provider = enrichment_gen if enrichment_gen in ("claude", "openai", "mock") else "mock"
        enricher = ContextualEnricher(generator=_create_generator(gen_provider))

    # Optional sparse retriever for BM25 index
    sparse_retriever = None
    if args.sparse_index_path:
        sparse_retriever = SparseRetriever(index_path=args.sparse_index_path)

    pipeline = IngestionPipeline(
        parser=DirectoryParser(),
        chunker=RecursiveChunker(chunk_config),
        embedder=_create_embedder(embedding_provider),
        store=QdrantStore(),
        collection_name=collection,
        enricher=enricher,
        sparse_retriever=sparse_retriever,
    )

    result = pipeline.run(source)

    output = {
        "success": len(result.errors) == 0,
        "documents_processed": result.documents_processed,
        "chunks_created": result.chunks_created,
        "chunks_indexed": result.chunks_indexed,
        "enrichment_summaries": result.enrichment_summaries,
        "errors": result.errors,
    }
    json.dump(output, sys.stdout)


def cmd_query(args: argparse.Namespace) -> None:
    """Run the query command."""
    try:
        config = json.loads(args.config_json) if args.config_json else {}
    except json.JSONDecodeError as e:
        json.dump({"success": False, "errors": [f"Invalid --config-json: {e}"]}, sys.stdout)
        sys.exit(1)

    embedding_provider = args.embedding or config.get("embedding_provider", "mock")
    generator_provider = args.generator or config.get("generator_provider", "mock")
    collection = args.collection or config.get("collection_name", "rag-forge")
    top_k = int(args.top_k)
    strategy = args.strategy
    alpha = float(args.alpha)
    reranker_type = args.reranker
    cohere_api_key = config.get("cohere_api_key")

    from rag_forge_core.query.engine import QueryEngine

    embedder = _create_embedder(embedding_provider)
    store = QdrantStore()
    dense = DenseRetriever(embedder=embedder, store=store, collection_name=collection)

    retriever: DenseRetriever | SparseRetriever | HybridRetriever
    if strategy == "dense":
        retriever = dense
    elif strategy == "sparse":
        sparse = SparseRetriever(index_path=args.sparse_index_path)
        retriever = sparse
    elif strategy == "hybrid":
        sparse = SparseRetriever(index_path=args.sparse_index_path)
        reranker = _create_reranker(reranker_type, cohere_api_key)
        retriever = HybridRetriever(
            dense=dense, sparse=sparse, alpha=alpha, reranker=reranker
        )
    else:
        json.dump(
            {"success": False, "errors": [f"Unknown strategy: {strategy!r}"]},
            sys.stdout,
        )
        sys.exit(1)

    engine = QueryEngine(retriever=retriever, generator=_create_generator(generator_provider), top_k=top_k)
    result = engine.query(args.question)
    output = {
        "answer": result.answer,
        "model_used": result.model_used,
        "chunks_retrieved": result.chunks_retrieved,
        "sources": [
            {
                "text": s.text[:200],
                "score": s.score,
                "id": s.chunk_id,
                "source_document": s.source_document,
            }
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
    index_parser.add_argument("--enrich", action="store_true", help="Enable contextual enrichment")
    index_parser.add_argument("--sparse-index-path", help="Path to persist BM25 sparse index")
    index_parser.add_argument(
        "--enrichment-generator",
        help="Generator for summaries: claude | openai | mock",
    )

    query_parser = subparsers.add_parser("query", help="Query the RAG pipeline")
    query_parser.add_argument("--question", required=True, help="The question to ask")
    query_parser.add_argument("--embedding", help="Embedding provider: openai | local | mock")
    query_parser.add_argument("--generator", help="Generation provider: claude | openai | mock")
    query_parser.add_argument("--collection", help="Collection name")
    query_parser.add_argument("--top-k", default="5", help="Number of chunks to retrieve")
    query_parser.add_argument("--config-json", help="JSON config from TS CLI")
    query_parser.add_argument(
        "--strategy", default="dense", help="Retrieval strategy: dense | sparse | hybrid"
    )
    query_parser.add_argument(
        "--alpha", default="0.6", help="RRF alpha for hybrid retrieval (0.0-1.0)"
    )
    query_parser.add_argument(
        "--reranker", default="none", help="Reranker: none | cohere | bge-local"
    )
    query_parser.add_argument("--sparse-index-path", help="Path to BM25 sparse index")

    args = parser.parse_args()
    if args.command == "index":
        cmd_index(args)
    elif args.command == "query":
        cmd_query(args)


if __name__ == "__main__":
    main()
