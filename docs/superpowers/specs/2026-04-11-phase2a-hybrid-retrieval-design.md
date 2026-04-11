# Phase 2A: Hybrid Retrieval, Reranking & Contextual Enrichment Design Spec

## Context

RAG-Forge Phase 1 delivered a working pipeline: parse → chunk → embed → store → query → audit. The query path currently uses dense-only retrieval (Qdrant vector search). Phase 2A upgrades the retrieval engine to hybrid search (dense + sparse), adds reranking, and introduces contextual enrichment at index time. These are the core pipeline improvements that everything else in Phase 2 builds on.

## Scope

**In scope:**
- BM25 sparse retrieval via `bm25s` library with file-based persistence
- Dense retriever adapter wrapping existing `QdrantStore`
- Hybrid retriever composing dense + sparse with Reciprocal Rank Fusion (RRF)
- Configurable alpha weighting (global default + per-query CLI override)
- Reranker protocol with Cohere Rerank API and BGE local implementations
- Mock reranker for testing
- Contextual enrichment: document-level summary prepending at index time
- `RetrievalConfig` Pydantic model for validation
- Updated `QueryEngine` to use `RetrieverProtocol` instead of raw `VectorStore`
- Updated `IngestionPipeline` with optional enrichment stage
- Updated CLI `query` command with `--strategy` and `--alpha` flags
- Updated Python CLI entry point for new retrieval options
- Unit and integration tests for all new components

**Out of scope:** Adaptive query routing (Phase 4), multi-query decomposition (Phase 2D), security guards (Phase 2B), evaluation enhancements (Phase 2C), MCP server wiring (Phase 2D), semantic caching (Phase 3).

## Architecture

Strategy pattern with composition. The `HybridRetriever` composes a `DenseRetriever` and `SparseRetriever` behind the existing `RetrieverProtocol`. An optional `Reranker` post-processes merged results. The `ContextualEnricher` is an optional stage in the `IngestionPipeline`.

```
Index time:

  rag-forge index --source ./docs --enrich
         │
         ▼
    TypeScript CLI (index command)
         │
         ▼ (Python bridge: uv run python -m rag_forge_core.cli)
         │
    IngestionPipeline.run(source_path)
         │
         ├─ 1. DirectoryParser.parse_directory(source_path)
         │      └─ Returns: list[Document]
         │
         ├─ 2. ChunkStrategy.chunk(document.text, document.source_path)
         │      └─ Returns: list[Chunk]
         │
         ├─ 3. ContextualEnricher.enrich(document, chunks)  [NEW, optional]
         │      └─ Generates document summary via GenerationProvider
         │      └─ Prepends summary to each chunk's text
         │      └─ Stores original text + summary in chunk metadata
         │      └─ Returns: list[Chunk] (with enriched text)
         │
         ├─ 4. EmbeddingProvider.embed(chunk_texts)
         │      └─ Embeddings now capture document-level context
         │      └─ Returns: list[list[float]]
         │
         ├─ 5. VectorStore.upsert(collection, items)  [dense index]
         │      └─ Returns: count indexed
         │
         └─ 6. SparseIndex.index(chunks)  [NEW, sparse index]
                └─ BM25 index built from chunk texts
                └─ Persisted to disk at sparse_index_path


Query time:

  rag-forge query "question" --strategy hybrid --alpha 0.6
         │
         ▼
    TypeScript CLI (query command)
         │
         ▼ (Python bridge)
         │
    QueryEngine.query(question)
         │
         ├─ RetrieverProtocol.retrieve(query, top_k)
         │      │
         │      ├─ If strategy=dense:
         │      │    └─ DenseRetriever.retrieve(query, top_k)
         │      │         └─ Embed query → QdrantStore.search()
         │      │
         │      ├─ If strategy=sparse:
         │      │    └─ SparseRetriever.retrieve(query, top_k)
         │      │         └─ BM25 search over indexed chunks
         │      │
         │      └─ If strategy=hybrid:
         │           └─ HybridRetriever.retrieve(query, top_k)
         │                ├─ DenseRetriever.retrieve(query, top_k * 2)
         │                ├─ SparseRetriever.retrieve(query, top_k * 2)
         │                └─ RRF merge with alpha → top_k results
         │
         ├─ [Optional] Reranker.rerank(query, results, top_k)
         │      └─ CohereReranker | BGELocalReranker | MockReranker
         │      └─ Re-scores and re-orders results
         │
         └─ GenerationProvider.generate(system_prompt, context + question)
              └─ Returns: QueryResult
```

## Components

### 1. Retrieval Configuration

**Location:** `packages/core/src/rag_forge_core/retrieval/config.py`

```python
from enum import Enum
from pydantic import BaseModel, Field


class RetrievalStrategy(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


class RerankerType(str, Enum):
    NONE = "none"
    COHERE = "cohere"
    BGE_LOCAL = "bge-local"


class RetrievalConfig(BaseModel):
    """Validated retrieval configuration (fail-fast via Pydantic)."""

    strategy: RetrievalStrategy = RetrievalStrategy.DENSE
    alpha: float = Field(default=0.6, ge=0.0, le=1.0)
    top_k: int = Field(default=5, ge=1, le=100)
    sparse_index_path: str | None = None
    reranker: RerankerType = RerankerType.NONE
    cohere_model: str = "rerank-v3.5"
    cohere_api_key: str | None = None
    bge_model_name: str = "BAAI/bge-reranker-v2-m3"
```

Alpha semantics: `alpha=1.0` is pure dense, `alpha=0.0` is pure sparse, `alpha=0.6` (default) weights dense at 60%.

Validation: Pydantic validates at init time (fail-fast pattern, consistent with `ChunkConfig`). If `strategy=hybrid` and `sparse_index_path` is None, the `SparseRetriever` defaults to in-memory mode.

### 2. Dense Retriever

**Location:** `packages/core/src/rag_forge_core/retrieval/dense.py`

```python
class DenseRetriever:
    """Wraps EmbeddingProvider + VectorStore into RetrieverProtocol."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection_name: str = "rag-forge",
    ) -> None: ...

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Embed query → vector search → convert SearchResult to RetrievalResult."""
        ...

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Not used directly — indexing goes through IngestionPipeline."""
        ...
```

This is a thin adapter. It embeds the query via `EmbeddingProvider.embed([query])[0]`, calls `VectorStore.search(collection, vector, top_k)`, and converts each `SearchResult` to a `RetrievalResult`. The `index()` method raises `NotImplementedError` — indexing is handled by `IngestionPipeline`, not the retriever.

### 3. Sparse Retriever

**Location:** `packages/core/src/rag_forge_core/retrieval/sparse.py`

```python
class SparseRetriever:
    """BM25-based sparse retrieval using the bm25s library."""

    def __init__(
        self,
        index_path: str | None = None,
    ) -> None: ...

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Tokenize query → BM25 search → return scored results."""
        ...

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Build BM25 index from chunk texts. Persists to disk if index_path set."""
        ...

    def save(self) -> None:
        """Persist current BM25 index to disk."""
        ...

    def load(self) -> None:
        """Load BM25 index from disk."""
        ...
```

Dependencies: `bm25s` library (add to `pyproject.toml`).

The `chunks` parameter for `index()` expects `list[dict]` where each dict has required keys `id` (str) and `text` (str), and an optional `metadata` key (dict). Example: `{"id": "abc-123", "text": "chunk content", "metadata": {"source_document": "readme.md"}}`. This matches what `IngestionPipeline` produces when converting `VectorItem` objects.

Persistence: If `index_path` is provided, `index()` automatically calls `save()` after building. On construction, if `index_path` exists on disk, `load()` is called automatically.

Tokenization: Uses `bm25s.tokenize()` which handles lowercasing and splitting. No stemming by default (keeps it simple; can be configured later).

### 4. Hybrid Retriever

**Location:** `packages/core/src/rag_forge_core/retrieval/hybrid.py`

```python
class HybridRetriever:
    """Combines dense + sparse retrieval with Reciprocal Rank Fusion."""

    def __init__(
        self,
        dense: DenseRetriever,
        sparse: SparseRetriever,
        alpha: float = 0.6,
        reranker: RerankerProtocol | None = None,
    ) -> None: ...

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Run both retrievers, merge via RRF, optionally rerank."""
        ...

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Index chunks into the sparse index (dense indexing is separate)."""
        ...
```

RRF algorithm:
1. Retrieve `top_k * 2` results from each retriever (over-fetch to ensure enough unique results after merge).
2. For each result, compute RRF score: `score = alpha * (1 / (k + rank_dense)) + (1 - alpha) * (1 / (k + rank_sparse))` where `k=60` (standard RRF constant). Results appearing in only one list get score from that list only.
3. Deduplicate by `chunk_id`, keeping the higher score.
4. Sort by RRF score descending, take top `top_k`.
5. If `reranker` is provided, pass the top results through `reranker.rerank(query, results, top_k)`.

Alpha override: The `alpha` parameter can be set per-query via the CLI `--alpha` flag. The `HybridRetriever` accepts it at construction, and the `QueryEngine` passes through the per-query value.

### 5. Reranker Protocol and Implementations

**Location:** `packages/core/src/rag_forge_core/retrieval/reranker.py`

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class RerankerProtocol(Protocol):
    """Protocol for all reranker implementations."""

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Re-score and re-order retrieval results."""
        ...

    def model_name(self) -> str:
        """Return the reranker model name."""
        ...


class CohereReranker:
    """Reranker using the Cohere Rerank API."""

    def __init__(
        self,
        api_key: str,
        model: str = "rerank-v3.5",
    ) -> None: ...

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Call Cohere Rerank API, update scores, re-sort."""
        ...

    def model_name(self) -> str:
        return self._model


class BGELocalReranker:
    """Local cross-encoder reranker using BAAI/bge-reranker-v2-m3."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
    ) -> None: ...

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Score each (query, chunk) pair with cross-encoder, re-sort."""
        ...

    def model_name(self) -> str:
        return self._model_name


class MockReranker:
    """Deterministic reranker for testing. Reverses result order."""

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Reverse the input order (deterministic, predictable in tests)."""
        return list(reversed(results))[:top_k]

    def model_name(self) -> str:
        return "mock-reranker"
```

Dependencies:
- `CohereReranker`: `cohere` Python SDK (optional dependency).
- `BGELocalReranker`: `sentence-transformers` (already an optional dep for `LocalEmbedder`).
- `MockReranker`: no dependencies.

Error handling: `CohereReranker` catches API errors and falls through gracefully — if reranking fails, it returns the original results unchanged with a logged warning (never crash the query pipeline because reranking failed).

### 6. Contextual Enricher

**Location:** `packages/core/src/rag_forge_core/context/enricher.py`

```python
from dataclasses import dataclass

from rag_forge_core.chunking.base import Chunk
from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.parsing.base import Document


@dataclass
class EnrichmentResult:
    """Result of contextual enrichment for a single document."""

    document_source: str
    summary: str
    chunks_enriched: int


class ContextualEnricher:
    """Prepends document-level summaries to chunks before embedding.

    Implements the Anthropic contextual retrieval technique: a short summary
    of the entire document is generated via an LLM, then prepended to each
    chunk's text. This gives the embedding model document-level context,
    improving retrieval accuracy by 2-18%.
    """

    def __init__(
        self,
        generator: GenerationProvider,
        max_document_tokens: int = 8000,
    ) -> None: ...

    def enrich(self, document: Document, chunks: list[Chunk]) -> list[Chunk]:
        """Generate a document summary and prepend it to each chunk.

        Returns new Chunk objects with enriched text. Original text is
        preserved in chunk.metadata["original_text"]. The summary is
        stored in chunk.metadata["document_summary"].
        """
        ...

    def _generate_summary(self, document: Document) -> str:
        """Generate a concise summary of the document for contextual enrichment."""
        ...
```

Summary generation prompt:
```
System: You are a document summarizer. Generate a concise 2-3 sentence summary
of the following document. Focus on the main topic, key entities, and the
document's purpose. This summary will be prepended to individual chunks to
provide context for embedding.

User: <document_text (truncated to max_document_tokens)>
```

Enriched chunk format: The chunk's `text` field becomes `"[Document context: {summary}]\n\n{original_text}"`. The original text is preserved in `metadata["original_text"]` and the summary in `metadata["document_summary"]`.

Token limit: If the document exceeds `max_document_tokens`, the text is truncated before sending to the LLM. This prevents excessive cost on very large documents.

Mock support: When using `MockGenerator`, the summary will be deterministic (the mock returns a fixed string), which is fine for testing that the enrichment pipeline works correctly.

### 7. Updated IngestionPipeline

**Location:** `packages/core/src/rag_forge_core/ingestion/pipeline.py` (modify existing)

Changes:
1. Add optional `enricher: ContextualEnricher | None = None` parameter to constructor.
2. Add optional `sparse_retriever: SparseRetriever | None = None` parameter to constructor.
3. After chunking (step 2), if `enricher` is set, call `enricher.enrich(document, chunks)` for each document's chunks. This replaces the chunk list with enriched chunks.
4. After vector store upsert (step 5), if `sparse_retriever` is set, call `sparse_retriever.index(chunk_dicts)` to build the BM25 index.
5. Update `IngestionResult` to include `enrichment_summaries: int` count.

The enrichment step runs per-document (not per-batch) because the summary is document-specific. This means one LLM call per document, not per chunk.

### 8. Updated QueryEngine

**Location:** `packages/core/src/rag_forge_core/query/engine.py` (modify existing)

Changes:
1. Replace direct `VectorStore` + `EmbeddingProvider` usage with `RetrieverProtocol`.
2. Constructor accepts `retriever: RetrieverProtocol` instead of `embedder` + `store`.
3. The `query()` method calls `retriever.retrieve(question, top_k)` and converts `RetrievalResult` to the existing `SearchResult` format for backward compatibility with the generation step.
4. Add optional `alpha: float | None` parameter to `query()` for per-query override (only applies when retriever is `HybridRetriever`).

```python
class QueryEngine:
    """Executes RAG queries using any RetrieverProtocol implementation."""

    def __init__(
        self,
        retriever: RetrieverProtocol,
        generator: GenerationProvider,
        top_k: int = 5,
    ) -> None: ...

    def query(self, question: str, alpha: float | None = None) -> QueryResult:
        """Execute a RAG query. Optional alpha override for hybrid retrieval."""
        ...
```

Backward compatibility: The `QueryResult` dataclass keeps its existing fields (`answer`, `sources`, `model_used`, `chunks_retrieved`). The `sources` field type changes from `list[SearchResult]` to `list[RetrievalResult]` since `RetrievalResult` carries more information (source_document, metadata).

### 9. Updated CLI Commands

**Location:** `packages/cli/src/commands/query.ts` (modify existing)

New flags:
- `--strategy <type>`: Retrieval strategy: `dense` | `sparse` | `hybrid` (default: `dense`)
- `--alpha <number>`: RRF alpha weighting for hybrid retrieval (default: `0.6`)
- `--reranker <type>`: Reranker: `none` | `cohere` | `bge-local` (default: `none`)

**Location:** `packages/cli/src/commands/index.ts` (modify existing)

New flags:
- `--enrich`: Enable contextual enrichment (document summary prepending)
- `--sparse-index-path <path>`: Path to persist BM25 sparse index (default: `.rag-forge/sparse-index`)
- `--enrichment-generator <provider>`: Generator for summaries: `claude` | `openai` | `mock` (default: same as `--generator`)

### 10. Updated Python CLI Entry Point

**Location:** `packages/core/src/rag_forge_core/cli.py` (modify existing)

Changes:
1. `index` subcommand: Accept `--enrich`, `--sparse-index-path`, `--enrichment-generator` args. When `--enrich` is set, construct `ContextualEnricher` with the specified generator and pass to `IngestionPipeline`.
2. `query` subcommand: Accept `--strategy`, `--alpha`, `--reranker` args. Construct the appropriate retriever based on strategy:
   - `dense`: `DenseRetriever(embedder, store)`
   - `sparse`: `SparseRetriever(index_path)`
   - `hybrid`: `HybridRetriever(dense, sparse, alpha, reranker)`
3. Construct optional reranker based on `--reranker` flag.

### 11. Updated __init__.py Exports

**Location:** `packages/core/src/rag_forge_core/retrieval/__init__.py`

Update to export all new types:
```python
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.config import RetrievalConfig, RetrievalStrategy, RerankerType
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.sparse import SparseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import (
    RerankerProtocol,
    CohereReranker,
    BGELocalReranker,
    MockReranker,
)

__all__ = [
    "RetrievalResult", "RetrieverProtocol",
    "RetrievalConfig", "RetrievalStrategy", "RerankerType",
    "DenseRetriever", "SparseRetriever", "HybridRetriever",
    "RerankerProtocol", "CohereReranker", "BGELocalReranker", "MockReranker",
]
```

**Location:** `packages/core/src/rag_forge_core/context/__init__.py`

Update to export enricher:
```python
from rag_forge_core.context.manager import ContextManager, ContextWindow
from rag_forge_core.context.enricher import ContextualEnricher, EnrichmentResult

__all__ = ["ContextManager", "ContextWindow", "ContextualEnricher", "EnrichmentResult"]
```

## Dependencies

### New Python dependencies (packages/core/pyproject.toml)

```toml
[project]
dependencies = [
    # ... existing deps ...
    "bm25s>=0.2",           # BM25 sparse retrieval
]

[project.optional-dependencies]
cohere = ["cohere>=5.0"]    # Cohere Rerank API
# sentence-transformers already in optional-dependencies for local embeddings
```

### No new TypeScript dependencies

The CLI changes are flag additions only — no new npm packages needed.

## Testing Strategy

### Unit Tests

**Location:** `packages/core/tests/`

1. `test_dense_retriever.py` — Verify adapter correctly wraps MockEmbedder + QdrantStore. Test empty collection handling.

2. `test_sparse_retriever.py` — Test BM25 indexing and retrieval with small corpus. Test persistence (save/load round-trip). Test empty index behavior.

3. `test_hybrid_retriever.py` — Test RRF merge logic with known dense + sparse rankings. Verify alpha=1.0 gives pure dense results. Verify alpha=0.0 gives pure sparse results. Test deduplication of results appearing in both lists.

4. `test_reranker.py` — Test MockReranker produces reversed results. Test CohereReranker and BGELocalReranker with mocked API responses (don't call real APIs in unit tests).

5. `test_enricher.py` — Test that enrichment prepends summary to chunk text. Test that original text is preserved in metadata. Test truncation of large documents. Test with MockGenerator.

6. `test_retrieval_config.py` — Test Pydantic validation: alpha bounds, strategy enum, reranker enum. Test invalid values are rejected.

### Integration Tests

7. `test_hybrid_pipeline_integration.py` — End-to-end test: index a small markdown corpus with enrichment enabled, query with hybrid retrieval, verify that results include expected chunks. Uses MockEmbedder + MockGenerator + MockReranker + in-memory stores.

## File Summary

### New files:
- `packages/core/src/rag_forge_core/retrieval/config.py`
- `packages/core/src/rag_forge_core/retrieval/dense.py`
- `packages/core/src/rag_forge_core/retrieval/sparse.py`
- `packages/core/src/rag_forge_core/retrieval/hybrid.py`
- `packages/core/src/rag_forge_core/retrieval/reranker.py`
- `packages/core/src/rag_forge_core/context/enricher.py`
- `packages/core/tests/test_dense_retriever.py`
- `packages/core/tests/test_sparse_retriever.py`
- `packages/core/tests/test_hybrid_retriever.py`
- `packages/core/tests/test_reranker.py`
- `packages/core/tests/test_enricher.py`
- `packages/core/tests/test_retrieval_config.py`
- `packages/core/tests/test_hybrid_pipeline_integration.py`

### Modified files:
- `packages/core/src/rag_forge_core/retrieval/__init__.py`
- `packages/core/src/rag_forge_core/context/__init__.py`
- `packages/core/src/rag_forge_core/ingestion/pipeline.py`
- `packages/core/src/rag_forge_core/query/engine.py`
- `packages/core/src/rag_forge_core/cli.py`
- `packages/cli/src/commands/query.ts`
- `packages/cli/src/commands/index.ts`
- `packages/core/pyproject.toml`
