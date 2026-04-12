"""Python CLI entry point for the rag-forge TypeScript bridge.

Called via: uv run python -m rag_forge_core.cli index --source ./docs --config-json '{...}'
Outputs JSON to stdout for the TypeScript CLI to parse and display.
"""

import argparse
import json
import sys
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.factory import create_chunker
from rag_forge_core.context.enricher import ContextualEnricher
from rag_forge_core.context.semantic_cache import SemanticCache
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.agentic import AgenticQueryEngine
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import RerankerProtocol
from rag_forge_core.retrieval.sparse import SparseRetriever
from rag_forge_core.security.faithfulness import FaithfulnessChecker
from rag_forge_core.security.injection import PromptInjectionClassifier, PromptInjectionDetector
from rag_forge_core.security.input_guard import InputGuard
from rag_forge_core.security.output_guard import OutputGuard
from rag_forge_core.security.pii import RegexPIIScanner
from rag_forge_core.security.rate_limiter import RateLimiter
from rag_forge_core.storage.qdrant import QdrantStore
from rag_forge_observability.tracing import TracingManager


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

    strategy = args.strategy
    chunk_config = ChunkConfig(
        strategy=strategy,
        chunk_size=chunk_size,
        overlap_ratio=overlap_ratio,
    )

    if strategy == "llm-driven" and not args.chunking_generator:
        json.dump(
            {"success": False, "errors": ["--chunking-generator is required for llm-driven strategy"]},
            sys.stdout,
        )
        sys.exit(1)

    embedder = _create_embedder(embedding_provider)
    chunker = create_chunker(
        config=chunk_config,
        embedder=embedder if strategy == "semantic" else None,
        generator=(
            _create_generator(args.chunking_generator)
            if strategy == "llm-driven"
            else None
        ),
    )

    # Optional enricher
    enricher = None
    if args.enrich:
        enrichment_gen = args.enrichment_generator or "mock"
        enricher = ContextualEnricher(generator=_create_generator(enrichment_gen))

    # Optional sparse retriever for BM25 index
    sparse_retriever = None
    if args.sparse_index_path:
        sparse_retriever = SparseRetriever(index_path=args.sparse_index_path)

    tracing = TracingManager()
    tracing.enable()
    tracer = tracing.get_tracer() if tracing.is_enabled() else None

    pipeline = IngestionPipeline(
        parser=DirectoryParser(),
        chunker=chunker,
        embedder=embedder,
        store=QdrantStore(),
        collection_name=collection,
        enricher=enricher,
        sparse_retriever=sparse_retriever,
        tracer=tracer,
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
    tracing.shutdown()


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

    if strategy in ("sparse", "hybrid") and not args.sparse_index_path:
        json.dump(
            {"success": False, "errors": [f"--sparse-index-path is required for {strategy} retrieval"]},
            sys.stdout,
        )
        sys.exit(1)

    if reranker_type != "none" and strategy != "hybrid":
        json.dump(
            {"success": False, "errors": ["--reranker is only supported with --strategy hybrid"]},
            sys.stdout,
        )
        sys.exit(1)

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

    # Build guards if enabled
    input_guard = None
    if args.input_guard:
        injection_classifier = None
        if generator_provider != "mock":
            injection_classifier = PromptInjectionClassifier(
                generator=_create_generator(generator_provider)
            )
        input_guard = InputGuard(
            injection_detector=PromptInjectionDetector(),
            injection_classifier=injection_classifier,
            pii_scanner=RegexPIIScanner(),
            rate_limiter=RateLimiter(
                max_queries=int(args.rate_limit),
                window_seconds=60,
            ),
        )

    output_guard = None
    if args.output_guard:
        output_guard = OutputGuard(
            faithfulness_checker=FaithfulnessChecker(
                generator=_create_generator(generator_provider),
                threshold=float(args.faithfulness_threshold),
            ),
            pii_scanner=RegexPIIScanner(),
        )

    # Build cache if enabled
    # Note: In-memory cache is session-scoped. For CLI one-shot usage,
    # caching is only effective when the MCP server handles multiple
    # queries in the same process. CLI flag exists for consistency.
    cache = None
    if args.cache:
        cache = SemanticCache(
            embedder=_create_embedder(embedding_provider),
            ttl_seconds=int(args.cache_ttl),
            similarity_threshold=float(args.cache_similarity),
        )

    tracing = TracingManager()
    tracing.enable()
    tracer = tracing.get_tracer() if tracing.is_enabled() else None

    _generator = _create_generator(generator_provider)
    engine: QueryEngine | AgenticQueryEngine
    if args.agent_mode:
        engine = AgenticQueryEngine(
            retriever=retriever,
            generator=_generator,
            top_k=top_k,
            input_guard=input_guard,
            output_guard=output_guard,
            tracer=tracer,
            cache=cache,
        )
    else:
        engine = QueryEngine(
            retriever=retriever,
            generator=_generator,
            top_k=top_k,
            input_guard=input_guard,
            output_guard=output_guard,
            tracer=tracer,
            cache=cache,
        )
    result = engine.query(args.question)
    output = {
        "answer": result.answer,
        "model_used": result.model_used,
        "chunks_retrieved": result.chunks_retrieved,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "cache_hit": cache is not None and cache.stats["hits"] > 0,
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
    tracing.shutdown()


def cmd_status(args: argparse.Namespace) -> None:
    """Check pipeline status."""
    collection = args.collection or "rag-forge"
    store = QdrantStore()
    try:
        count = store.count(collection)
        indexed = count > 0
    except (ValueError, KeyError):
        count = 0
        indexed = False

    output = {
        "indexed": indexed,
        "collection": collection,
        "chunk_count": count,
    }
    json.dump(output, sys.stdout)


def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect a specific chunk by ID."""
    collection = args.collection or "rag-forge"
    chunk_id = args.chunk_id
    store = QdrantStore()

    try:
        result = store.get_by_id(collection, chunk_id)
    except Exception as e:
        json.dump({"found": False, "chunk_id": chunk_id, "collection": collection, "error": str(e)}, sys.stdout)
        return

    if result is None:
        json.dump({"found": False, "chunk_id": chunk_id, "collection": collection}, sys.stdout)
        return
    output = {
        "found": True,
        "chunk_id": chunk_id,
        "text": result.text,
        "metadata": result.metadata,
        "collection": collection,
    }
    json.dump(output, sys.stdout)


def cmd_guardrails_test(args: argparse.Namespace) -> None:
    """Run adversarial test suite against security guards."""
    from rag_forge_core.security.adversarial import AdversarialRunner

    try:
        user_corpus = args.corpus if hasattr(args, "corpus") and args.corpus else None
        runner = AdversarialRunner(user_corpus_path=user_corpus)
        result = runner.run()
        output = {
            "success": True,
            "total_tested": result.total_tested,
            "blocked": result.blocked,
            "passed_through": result.passed_through,
            "pass_rate": result.pass_rate,
            "by_category": result.by_category,
            "failures": result.failures,
        }
    except Exception as e:
        output = {"success": False, "error": str(e)}
    json.dump(output, sys.stdout)


def cmd_guardrails_scan_pii(args: argparse.Namespace) -> None:
    """Scan vector store collection for PII."""
    from rag_forge_core.security.pii_scanner import PIICollectionScanner

    try:
        collection = args.collection or "rag-forge"
        store = QdrantStore()
        count = store.count(collection)
        all_chunks: list[dict[str, str]] = []
        points = store._client.scroll(collection_name=collection, limit=count)[0]
        for point in points:
            payload = dict(point.payload or {})
            text = str(payload.get("text", ""))
            chunk_id = str(payload.get("item_id", point.id))
            all_chunks.append({"id": chunk_id, "text": text})

        scanner = PIICollectionScanner()
        report = scanner.scan_chunks(all_chunks)
        output = {
            "success": True,
            "chunks_scanned": report.chunks_scanned,
            "chunks_with_pii": report.chunks_with_pii,
            "pii_types": report.pii_types,
            "affected_chunks": report.affected_chunks,
        }
    except Exception as e:
        output = {"success": False, "error": str(e)}
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
    index_parser.add_argument(
        "--strategy",
        default="recursive",
        help="Chunking strategy: fixed | recursive | semantic | structural | llm-driven",
    )
    index_parser.add_argument(
        "--chunking-generator",
        help="Generator for LLM-driven chunking: claude | openai | mock",
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
    query_parser.add_argument(
        "--input-guard", action="store_true", help="Enable input security guard"
    )
    query_parser.add_argument(
        "--output-guard", action="store_true", help="Enable output security guard"
    )
    query_parser.add_argument(
        "--faithfulness-threshold", default="0.85",
        help="Faithfulness score threshold (0.0-1.0)",
    )
    query_parser.add_argument(
        "--rate-limit", default="60",
        help="Max queries per minute",
    )
    query_parser.add_argument("--cache", action="store_true", help="Enable semantic query caching")
    query_parser.add_argument("--cache-ttl", default="3600", help="Cache TTL in seconds")
    query_parser.add_argument("--cache-similarity", default="0.95", help="Cosine similarity threshold")
    query_parser.add_argument("--agent-mode", action="store_true", help="Enable multi-query decomposition for complex questions")

    status_parser = subparsers.add_parser("status", help="Check pipeline status")
    status_parser.add_argument("--collection", help="Collection name", default="rag-forge")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a chunk by ID")
    inspect_parser.add_argument("--chunk-id", required=True, help="The chunk ID to inspect")
    inspect_parser.add_argument("--collection", help="Collection name", default="rag-forge")

    guardrails_test_parser = subparsers.add_parser("guardrails-test", help="Run adversarial test suite")
    guardrails_test_parser.add_argument("--corpus", help="Path to custom adversarial corpus JSON")

    guardrails_scan_parser = subparsers.add_parser("guardrails-scan-pii", help="Scan collection for PII")
    guardrails_scan_parser.add_argument("--collection", help="Collection name", default="rag-forge")

    args = parser.parse_args()
    if args.command == "index":
        cmd_index(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "guardrails-test":
        cmd_guardrails_test(args)
    elif args.command == "guardrails-scan-pii":
        cmd_guardrails_scan_pii(args)


if __name__ == "__main__":
    main()
