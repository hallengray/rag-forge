# Phase 2A: Hybrid Retrieval, Reranking & Contextual Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the retrieval engine from dense-only to hybrid search (BM25 + dense + RRF fusion), add reranking (Cohere + BGE local), and add contextual enrichment (document summary prepending at index time).

**Architecture:** Strategy pattern with composition. `HybridRetriever` composes `DenseRetriever` + `SparseRetriever` behind the existing `RetrieverProtocol`. An optional `RerankerProtocol` post-processes merged results. `ContextualEnricher` is an optional stage in `IngestionPipeline` between chunking and embedding. The `QueryEngine` is updated to accept any `RetrieverProtocol` instead of raw `VectorStore` + `EmbeddingProvider`.

**Tech Stack:** Python 3.11+ (bm25s, cohere, sentence-transformers, pydantic), TypeScript (Commander.js), pytest, vitest.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/core/src/rag_forge_core/retrieval/config.py` | `RetrievalConfig`, `RetrievalStrategy`, `RerankerType` Pydantic models |
| `packages/core/src/rag_forge_core/retrieval/dense.py` | `DenseRetriever` — adapts EmbeddingProvider + VectorStore to RetrieverProtocol |
| `packages/core/src/rag_forge_core/retrieval/sparse.py` | `SparseRetriever` — BM25 via bm25s with file persistence |
| `packages/core/src/rag_forge_core/retrieval/hybrid.py` | `HybridRetriever` — RRF fusion of dense + sparse with optional reranker |
| `packages/core/src/rag_forge_core/retrieval/reranker.py` | `RerankerProtocol`, `CohereReranker`, `BGELocalReranker`, `MockReranker` |
| `packages/core/src/rag_forge_core/context/enricher.py` | `ContextualEnricher` — document summary prepending |
| `packages/core/tests/test_retrieval_config.py` | Pydantic validation tests for RetrievalConfig |
| `packages/core/tests/test_dense_retriever.py` | DenseRetriever adapter tests |
| `packages/core/tests/test_sparse_retriever.py` | BM25 index, search, persistence tests |
| `packages/core/tests/test_hybrid_retriever.py` | RRF merge, alpha, dedup tests |
| `packages/core/tests/test_reranker.py` | MockReranker and reranker protocol tests |
| `packages/core/tests/test_enricher.py` | Contextual enrichment tests |
| `packages/core/tests/test_hybrid_pipeline_integration.py` | End-to-end: index with enrichment → query with hybrid retrieval |

### Modified Files

| File | Change |
|------|--------|
| `packages/core/pyproject.toml` | Add `bm25s` dep, `cohere` optional dep |
| `packages/core/src/rag_forge_core/retrieval/__init__.py` | Export all new retrieval types |
| `packages/core/src/rag_forge_core/context/__init__.py` | Export enricher types |
| `packages/core/src/rag_forge_core/ingestion/pipeline.py` | Add optional enricher + sparse indexing stages |
| `packages/core/src/rag_forge_core/query/engine.py` | Accept RetrieverProtocol instead of VectorStore + EmbeddingProvider |
| `packages/core/src/rag_forge_core/cli.py` | Add retrieval/enrichment args to index + query subcommands |
| `packages/cli/src/commands/index.ts` | Add `--enrich`, `--sparse-index-path` flags |
| `packages/cli/src/commands/query.ts` | Add `--strategy`, `--alpha`, `--reranker` flags |

---

## Task 1: Add bm25s Dependency

**Files:**
- Modify: `packages/core/pyproject.toml`

- [ ] **Step 1: Update pyproject.toml with new dependencies**

Add `bm25s` to dependencies and `cohere` to optional dependencies:

```toml
[project]
name = "rag-forge-core"
version = "0.1.0"
description = "RAG pipeline primitives: ingestion, retrieval, context management, and security"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "pydantic>=2.0",
    "rich>=13.0",
    "tiktoken>=0.7",
    "pymupdf>=1.24",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "openai>=1.30",
    "qdrant-client>=1.9",
    "bm25s>=0.2",
]

[project.optional-dependencies]
local = ["sentence-transformers>=3.0"]
cohere = ["cohere>=5.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/rag_forge_core"]
```

- [ ] **Step 2: Install updated dependencies**

Run: `cd packages/core && uv sync`
Expected: Successful install including bm25s.

- [ ] **Step 3: Verify bm25s is importable**

Run: `cd packages/core && uv run python -c "import bm25s; print(bm25s.__version__)"`
Expected: Version number printed (e.g., `0.2.x`).

- [ ] **Step 4: Commit**

```bash
git add packages/core/pyproject.toml
git commit -m "chore(core): add bm25s dependency and cohere optional dep"
```

---

## Task 2: RetrievalConfig Pydantic Model

**Files:**
- Create: `packages/core/src/rag_forge_core/retrieval/config.py`
- Test: `packages/core/tests/test_retrieval_config.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_retrieval_config.py`:

```python
"""Tests for retrieval configuration validation."""

import pytest
from pydantic import ValidationError

from rag_forge_core.retrieval.config import RerankerType, RetrievalConfig, RetrievalStrategy


class TestRetrievalStrategy:
    def test_dense_is_default(self) -> None:
        config = RetrievalConfig()
        assert config.strategy == RetrievalStrategy.DENSE

    def test_valid_strategies(self) -> None:
        for strategy in ("dense", "sparse", "hybrid"):
            config = RetrievalConfig(strategy=strategy)
            assert config.strategy == RetrievalStrategy(strategy)

    def test_invalid_strategy_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(strategy="invalid")


class TestAlpha:
    def test_default_alpha(self) -> None:
        config = RetrievalConfig()
        assert config.alpha == 0.6

    def test_alpha_bounds(self) -> None:
        RetrievalConfig(alpha=0.0)
        RetrievalConfig(alpha=1.0)

    def test_alpha_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(alpha=-0.1)

    def test_alpha_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(alpha=1.1)


class TestReranker:
    def test_default_reranker_is_none(self) -> None:
        config = RetrievalConfig()
        assert config.reranker == RerankerType.NONE

    def test_valid_reranker_types(self) -> None:
        for reranker in ("none", "cohere", "bge-local"):
            config = RetrievalConfig(reranker=reranker)
            assert config.reranker == RerankerType(reranker)

    def test_invalid_reranker_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(reranker="invalid")


class TestTopK:
    def test_default_top_k(self) -> None:
        config = RetrievalConfig()
        assert config.top_k == 5

    def test_top_k_minimum(self) -> None:
        config = RetrievalConfig(top_k=1)
        assert config.top_k == 1

    def test_top_k_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(top_k=0)

    def test_top_k_over_100_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(top_k=101)


class TestSparseIndexPath:
    def test_default_sparse_index_path_is_none(self) -> None:
        config = RetrievalConfig()
        assert config.sparse_index_path is None

    def test_custom_sparse_index_path(self) -> None:
        config = RetrievalConfig(sparse_index_path="/tmp/bm25-index")
        assert config.sparse_index_path == "/tmp/bm25-index"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_retrieval_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag_forge_core.retrieval.config'`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/retrieval/config.py`:

```python
"""Retrieval configuration with Pydantic validation (fail-fast)."""

from enum import Enum

from pydantic import BaseModel, Field


class RetrievalStrategy(str, Enum):
    """Available retrieval strategies."""

    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


class RerankerType(str, Enum):
    """Available reranker implementations."""

    NONE = "none"
    COHERE = "cohere"
    BGE_LOCAL = "bge-local"


class RetrievalConfig(BaseModel):
    """Validated retrieval configuration.

    Validates at init time (fail-fast pattern, consistent with ChunkConfig).
    """

    strategy: RetrievalStrategy = RetrievalStrategy.DENSE
    alpha: float = Field(default=0.6, ge=0.0, le=1.0)
    top_k: int = Field(default=5, ge=1, le=100)
    sparse_index_path: str | None = None
    reranker: RerankerType = RerankerType.NONE
    cohere_model: str = "rerank-v3.5"
    cohere_api_key: str | None = None
    bge_model_name: str = "BAAI/bge-reranker-v2-m3"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_retrieval_config.py -v`
Expected: All 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/retrieval/config.py packages/core/tests/test_retrieval_config.py
git commit -m "feat(core): add RetrievalConfig pydantic model with validation"
```

---

## Task 3: DenseRetriever

**Files:**
- Create: `packages/core/src/rag_forge_core/retrieval/dense.py`
- Test: `packages/core/tests/test_dense_retriever.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_dense_retriever.py`:

```python
"""Tests for the dense retriever adapter."""

from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.storage.base import VectorItem
from rag_forge_core.storage.qdrant import QdrantStore


class TestDenseRetriever:
    def _setup_store(self) -> tuple[QdrantStore, MockEmbedder]:
        """Create a store with 3 indexed documents."""
        store = QdrantStore()
        embedder = MockEmbedder(dimension=384)
        store.create_collection("test", dimension=384)
        texts = ["Python is great", "JavaScript is popular", "Rust is fast"]
        vectors = embedder.embed(texts)
        items = [
            VectorItem(
                id=str(i),
                vector=v,
                text=t,
                metadata={"source_document": f"doc{i}.md"},
            )
            for i, (t, v) in enumerate(zip(texts, vectors, strict=True))
        ]
        store.upsert("test", items)
        return store, embedder

    def test_implements_protocol(self) -> None:
        store = QdrantStore()
        embedder = MockEmbedder()
        retriever = DenseRetriever(embedder=embedder, store=store)
        assert isinstance(retriever, RetrieverProtocol)

    def test_retrieve_returns_results(self) -> None:
        store, embedder = self._setup_store()
        retriever = DenseRetriever(
            embedder=embedder, store=store, collection_name="test"
        )
        results = retriever.retrieve("Python programming", top_k=2)
        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_retrieve_result_fields(self) -> None:
        store, embedder = self._setup_store()
        retriever = DenseRetriever(
            embedder=embedder, store=store, collection_name="test"
        )
        results = retriever.retrieve("Python", top_k=1)
        result = results[0]
        assert isinstance(result.chunk_id, str)
        assert isinstance(result.text, str)
        assert isinstance(result.score, float)
        assert isinstance(result.source_document, str)

    def test_retrieve_empty_collection(self) -> None:
        store = QdrantStore()
        embedder = MockEmbedder(dimension=384)
        store.create_collection("empty", dimension=384)
        retriever = DenseRetriever(
            embedder=embedder, store=store, collection_name="empty"
        )
        results = retriever.retrieve("anything", top_k=5)
        assert results == []

    def test_retrieve_nonexistent_collection(self) -> None:
        store = QdrantStore()
        embedder = MockEmbedder(dimension=384)
        retriever = DenseRetriever(
            embedder=embedder, store=store, collection_name="nonexistent"
        )
        results = retriever.retrieve("anything", top_k=5)
        assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_dense_retriever.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag_forge_core.retrieval.dense'`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/retrieval/dense.py`:

```python
"""Dense retriever: wraps EmbeddingProvider + VectorStore into RetrieverProtocol."""

from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.storage.base import VectorStore


class DenseRetriever:
    """Adapts EmbeddingProvider + VectorStore to the RetrieverProtocol interface."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection_name: str = "rag-forge",
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._collection_name = collection_name

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Embed query, search vector store, return RetrievalResults."""
        query_vector = self._embedder.embed([query])[0]
        try:
            search_results = self._store.search(
                self._collection_name, query_vector, top_k
            )
        except (ValueError, KeyError):
            return []

        return [
            RetrievalResult(
                chunk_id=r.id,
                text=r.text,
                score=r.score,
                source_document=r.metadata.get("source_document", ""),
                metadata=r.metadata,
            )
            for r in search_results
        ]

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Not used — dense indexing goes through IngestionPipeline."""
        raise NotImplementedError(
            "Dense indexing is handled by IngestionPipeline, not DenseRetriever."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_dense_retriever.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/retrieval/dense.py packages/core/tests/test_dense_retriever.py
git commit -m "feat(core): add DenseRetriever adapter for RetrieverProtocol"
```

---

## Task 4: SparseRetriever (BM25)

**Files:**
- Create: `packages/core/src/rag_forge_core/retrieval/sparse.py`
- Test: `packages/core/tests/test_sparse_retriever.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_sparse_retriever.py`:

```python
"""Tests for the BM25 sparse retriever."""

import tempfile
from pathlib import Path

from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.sparse import SparseRetriever


def _sample_chunks() -> list[dict[str, str]]:
    """Create a small corpus for testing."""
    return [
        {"id": "chunk-0", "text": "Python is a popular programming language"},
        {"id": "chunk-1", "text": "JavaScript runs in the browser"},
        {"id": "chunk-2", "text": "Rust provides memory safety without garbage collection"},
        {"id": "chunk-3", "text": "Python supports machine learning with libraries like PyTorch"},
        {"id": "chunk-4", "text": "TypeScript adds static types to JavaScript"},
    ]


class TestSparseRetriever:
    def test_implements_protocol(self) -> None:
        retriever = SparseRetriever()
        assert isinstance(retriever, RetrieverProtocol)

    def test_index_returns_count(self) -> None:
        retriever = SparseRetriever()
        count = retriever.index(_sample_chunks())
        assert count == 5

    def test_retrieve_returns_results(self) -> None:
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("Python programming", top_k=2)
        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_retrieve_result_fields(self) -> None:
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("Python", top_k=1)
        result = results[0]
        assert isinstance(result.chunk_id, str)
        assert isinstance(result.text, str)
        assert isinstance(result.score, float)
        assert result.score > 0.0

    def test_retrieve_keyword_relevance(self) -> None:
        """BM25 should rank documents containing the query terms higher."""
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("JavaScript browser", top_k=2)
        result_texts = [r.text for r in results]
        assert any("JavaScript" in t for t in result_texts)

    def test_retrieve_empty_index(self) -> None:
        retriever = SparseRetriever()
        results = retriever.retrieve("anything", top_k=5)
        assert results == []

    def test_retrieve_respects_top_k(self) -> None:
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("Python", top_k=1)
        assert len(results) == 1

    def test_top_k_larger_than_corpus(self) -> None:
        retriever = SparseRetriever()
        retriever.index(_sample_chunks())
        results = retriever.retrieve("Python", top_k=100)
        assert len(results) == 5


class TestSparseRetrieverPersistence:
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "bm25-index")
            retriever = SparseRetriever(index_path=index_path)
            retriever.index(_sample_chunks())
            retriever.save()

            loaded = SparseRetriever(index_path=index_path)
            loaded.load()
            results = loaded.retrieve("Python", top_k=2)
            assert len(results) == 2

    def test_auto_save_on_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "bm25-index")
            retriever = SparseRetriever(index_path=index_path)
            retriever.index(_sample_chunks())

            loaded = SparseRetriever(index_path=index_path)
            loaded.load()
            results = loaded.retrieve("Python", top_k=1)
            assert len(results) == 1

    def test_auto_load_on_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "bm25-index")
            retriever = SparseRetriever(index_path=index_path)
            retriever.index(_sample_chunks())

            auto_loaded = SparseRetriever(index_path=index_path)
            results = auto_loaded.retrieve("JavaScript", top_k=1)
            assert len(results) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_sparse_retriever.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag_forge_core.retrieval.sparse'`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/retrieval/sparse.py`:

```python
"""BM25-based sparse retrieval using the bm25s library."""

from pathlib import Path

import bm25s

from rag_forge_core.retrieval.base import RetrievalResult


class SparseRetriever:
    """BM25 sparse retriever with optional file-based persistence."""

    def __init__(self, index_path: str | None = None) -> None:
        self._index_path = index_path
        self._model: bm25s.BM25 | None = None
        self._chunk_ids: list[str] = []
        self._chunk_texts: list[str] = []

        if index_path and Path(index_path).exists():
            self.load()

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Tokenize query, search BM25 index, return scored results."""
        if self._model is None:
            return []

        query_tokens = bm25s.tokenize(query, show_progress=False)
        actual_top_k = min(top_k, len(self._chunk_ids))
        if actual_top_k == 0:
            return []

        results, scores = self._model.retrieve(
            query_tokens, k=actual_top_k, show_progress=False
        )

        retrieval_results: list[RetrievalResult] = []
        for i in range(actual_top_k):
            doc_idx = results[0, i]
            score = float(scores[0, i])
            if score <= 0.0:
                continue
            retrieval_results.append(
                RetrievalResult(
                    chunk_id=self._chunk_ids[doc_idx],
                    text=self._chunk_texts[doc_idx],
                    score=score,
                    source_document="",
                    metadata={"retriever": "bm25"},
                )
            )

        return retrieval_results

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Build BM25 index from chunk texts. Auto-saves if index_path is set."""
        self._chunk_ids = [c["id"] for c in chunks]
        self._chunk_texts = [c["text"] for c in chunks]

        corpus_tokens = bm25s.tokenize(self._chunk_texts, show_progress=False)
        self._model = bm25s.BM25()
        self._model.index(corpus_tokens, show_progress=False)

        if self._index_path:
            self.save()

        return len(chunks)

    def save(self) -> None:
        """Persist the BM25 index and metadata to disk."""
        if self._model is None or self._index_path is None:
            return
        import json

        path = Path(self._index_path)
        self._model.save(str(path), corpus=self._chunk_texts)

        metadata_path = path / "sparse_metadata.json"
        metadata_path.write_text(
            json.dumps({"chunk_ids": self._chunk_ids}), encoding="utf-8"
        )

    def load(self) -> None:
        """Load a BM25 index and metadata from disk."""
        if self._index_path is None:
            return
        import json

        path = Path(self._index_path)
        if not path.exists():
            return

        self._model = bm25s.BM25.load(str(path), load_corpus=True)
        self._chunk_texts = [str(doc) for doc in self._model.corpus]

        metadata_path = path / "sparse_metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self._chunk_ids = metadata["chunk_ids"]
        else:
            self._chunk_ids = [str(i) for i in range(len(self._chunk_texts))]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_sparse_retriever.py -v`
Expected: All 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/retrieval/sparse.py packages/core/tests/test_sparse_retriever.py
git commit -m "feat(core): add SparseRetriever with BM25 via bm25s library"
```

---

## Task 5: Reranker Protocol and Implementations

**Files:**
- Create: `packages/core/src/rag_forge_core/retrieval/reranker.py`
- Test: `packages/core/tests/test_reranker.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_reranker.py`:

```python
"""Tests for reranker protocol and implementations."""

from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.retrieval.reranker import MockReranker, RerankerProtocol


def _sample_results() -> list[RetrievalResult]:
    return [
        RetrievalResult(chunk_id="a", text="first", score=0.9, source_document="doc1.md"),
        RetrievalResult(chunk_id="b", text="second", score=0.8, source_document="doc2.md"),
        RetrievalResult(chunk_id="c", text="third", score=0.7, source_document="doc3.md"),
    ]


class TestMockReranker:
    def test_implements_protocol(self) -> None:
        reranker = MockReranker()
        assert isinstance(reranker, RerankerProtocol)

    def test_reverses_order(self) -> None:
        reranker = MockReranker()
        results = _sample_results()
        reranked = reranker.rerank("query", results, top_k=3)
        assert [r.chunk_id for r in reranked] == ["c", "b", "a"]

    def test_respects_top_k(self) -> None:
        reranker = MockReranker()
        results = _sample_results()
        reranked = reranker.rerank("query", results, top_k=2)
        assert len(reranked) == 2
        assert [r.chunk_id for r in reranked] == ["c", "b"]

    def test_model_name(self) -> None:
        reranker = MockReranker()
        assert reranker.model_name() == "mock-reranker"

    def test_empty_results(self) -> None:
        reranker = MockReranker()
        reranked = reranker.rerank("query", [], top_k=5)
        assert reranked == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_reranker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag_forge_core.retrieval.reranker'`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/retrieval/reranker.py`:

```python
"""Reranker protocol and implementations for post-retrieval re-scoring."""

import logging
from typing import Protocol, runtime_checkable

from rag_forge_core.retrieval.base import RetrievalResult

logger = logging.getLogger(__name__)


@runtime_checkable
class RerankerProtocol(Protocol):
    """Protocol for all reranker implementations."""

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]: ...

    def model_name(self) -> str: ...


class CohereReranker:
    """Reranker using the Cohere Rerank API.

    Requires the `cohere` package: pip install rag-forge-core[cohere]
    """

    def __init__(self, api_key: str, model: str = "rerank-v3.5") -> None:
        import cohere

        self._client = cohere.Client(api_key)
        self._model = model

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Call Cohere Rerank API, update scores, re-sort."""
        if not results:
            return []

        try:
            import cohere

            response = self._client.rerank(
                query=query,
                documents=[r.text for r in results],
                top_n=min(top_k, len(results)),
                model=self._model,
            )

            reranked: list[RetrievalResult] = []
            for item in response.results:
                original = results[item.index]
                reranked.append(
                    RetrievalResult(
                        chunk_id=original.chunk_id,
                        text=original.text,
                        score=item.relevance_score,
                        source_document=original.source_document,
                        metadata={**original.metadata, "reranker": self._model},
                    )
                )
            return reranked
        except Exception:
            logger.warning("Cohere reranking failed, returning original results", exc_info=True)
            return results[:top_k]

    def model_name(self) -> str:
        return self._model


class BGELocalReranker:
    """Local cross-encoder reranker using BAAI/bge-reranker-v2-m3.

    Requires sentence-transformers: pip install rag-forge-core[local]
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        from sentence_transformers import CrossEncoder

        self._model_name = model_name
        self._model = CrossEncoder(model_name)

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Score each (query, chunk) pair with cross-encoder, re-sort."""
        if not results:
            return []

        pairs = [[query, r.text] for r in results]
        scores = self._model.predict(pairs)

        scored = list(zip(results, scores, strict=True))
        scored.sort(key=lambda x: float(x[1]), reverse=True)

        return [
            RetrievalResult(
                chunk_id=r.chunk_id,
                text=r.text,
                score=float(s),
                source_document=r.source_document,
                metadata={**r.metadata, "reranker": self._model_name},
            )
            for r, s in scored[:top_k]
        ]

    def model_name(self) -> str:
        return self._model_name


class MockReranker:
    """Deterministic reranker for testing. Reverses result order."""

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 5
    ) -> list[RetrievalResult]:
        """Reverse the input order (deterministic, predictable in tests)."""
        _ = query
        return list(reversed(results))[:top_k]

    def model_name(self) -> str:
        return "mock-reranker"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_reranker.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/retrieval/reranker.py packages/core/tests/test_reranker.py
git commit -m "feat(core): add RerankerProtocol with Cohere, BGE local, and mock implementations"
```

---

## Task 6: HybridRetriever (RRF Fusion)

**Files:**
- Create: `packages/core/src/rag_forge_core/retrieval/hybrid.py`
- Test: `packages/core/tests/test_hybrid_retriever.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_hybrid_retriever.py`:

```python
"""Tests for hybrid retriever with Reciprocal Rank Fusion."""

from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import MockReranker
from rag_forge_core.retrieval.sparse import SparseRetriever
from rag_forge_core.storage.base import VectorItem
from rag_forge_core.storage.qdrant import QdrantStore

SAMPLE_TEXTS = [
    "Python is a popular programming language for data science",
    "JavaScript powers interactive web applications",
    "Rust provides memory safety without garbage collection",
    "Python machine learning uses libraries like scikit-learn",
    "TypeScript adds static typing to JavaScript code",
]


def _build_retrievers() -> tuple[DenseRetriever, SparseRetriever]:
    """Build dense + sparse retrievers with the same corpus."""
    embedder = MockEmbedder(dimension=384)
    store = QdrantStore()
    store.create_collection("test", dimension=384)

    vectors = embedder.embed(SAMPLE_TEXTS)
    items = [
        VectorItem(
            id=f"chunk-{i}",
            vector=v,
            text=t,
            metadata={"source_document": f"doc{i}.md"},
        )
        for i, (t, v) in enumerate(zip(SAMPLE_TEXTS, vectors, strict=True))
    ]
    store.upsert("test", items)

    dense = DenseRetriever(embedder=embedder, store=store, collection_name="test")

    sparse = SparseRetriever()
    sparse.index([{"id": f"chunk-{i}", "text": t} for i, t in enumerate(SAMPLE_TEXTS)])

    return dense, sparse


class TestHybridRetriever:
    def test_implements_protocol(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        assert isinstance(hybrid, RetrieverProtocol)

    def test_retrieve_returns_results(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        results = hybrid.retrieve("Python programming", top_k=3)
        assert len(results) > 0
        assert len(results) <= 3
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_results_sorted_by_score_descending(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        results = hybrid.retrieve("Python", top_k=5)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_no_duplicate_chunk_ids(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        results = hybrid.retrieve("Python programming", top_k=5)
        chunk_ids = [r.chunk_id for r in results]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_alpha_1_is_pure_dense(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse, alpha=1.0)
        hybrid_results = hybrid.retrieve("Python", top_k=3)
        dense_results = dense.retrieve("Python", top_k=3)
        assert [r.chunk_id for r in hybrid_results] == [
            r.chunk_id for r in dense_results
        ]

    def test_alpha_0_is_pure_sparse(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse, alpha=0.0)
        hybrid_results = hybrid.retrieve("Python", top_k=3)
        sparse_results = sparse.retrieve("Python", top_k=3)
        assert [r.chunk_id for r in hybrid_results] == [
            r.chunk_id for r in sparse_results
        ]

    def test_respects_top_k(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        results = hybrid.retrieve("Python", top_k=2)
        assert len(results) <= 2


class TestHybridRetrieverWithReranker:
    def test_reranker_is_applied(self) -> None:
        dense, sparse = _build_retrievers()
        reranker = MockReranker()
        hybrid = HybridRetriever(
            dense=dense, sparse=sparse, reranker=reranker
        )
        results_no_rerank = HybridRetriever(
            dense=dense, sparse=sparse
        ).retrieve("Python", top_k=3)
        results_with_rerank = hybrid.retrieve("Python", top_k=3)

        # MockReranker reverses order, so results should differ
        ids_no_rerank = [r.chunk_id for r in results_no_rerank]
        ids_with_rerank = [r.chunk_id for r in results_with_rerank]
        assert ids_no_rerank != ids_with_rerank or len(ids_no_rerank) <= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_hybrid_retriever.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag_forge_core.retrieval.hybrid'`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/retrieval/hybrid.py`:

```python
"""Hybrid retriever: combines dense + sparse with Reciprocal Rank Fusion."""

from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.reranker import RerankerProtocol
from rag_forge_core.retrieval.sparse import SparseRetriever

RRF_K = 60  # Standard RRF constant


class HybridRetriever:
    """Combines dense + sparse retrieval with Reciprocal Rank Fusion (RRF).

    Alpha controls the balance: 1.0 = pure dense, 0.0 = pure sparse.
    An optional reranker post-processes the merged results.
    """

    def __init__(
        self,
        dense: DenseRetriever,
        sparse: SparseRetriever,
        alpha: float = 0.6,
        reranker: RerankerProtocol | None = None,
    ) -> None:
        self._dense = dense
        self._sparse = sparse
        self._alpha = alpha
        self._reranker = reranker

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Run both retrievers, merge via RRF, optionally rerank."""
        fetch_k = top_k * 2

        dense_results = self._dense.retrieve(query, fetch_k) if self._alpha > 0 else []
        sparse_results = self._sparse.retrieve(query, fetch_k) if self._alpha < 1 else []

        merged = self._rrf_merge(dense_results, sparse_results, top_k)

        if self._reranker is not None:
            merged = self._reranker.rerank(query, merged, top_k)

        return merged

    def _rrf_merge(
        self,
        dense_results: list[RetrievalResult],
        sparse_results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Merge dense + sparse results using Reciprocal Rank Fusion."""
        scores: dict[str, float] = {}
        result_map: dict[str, RetrievalResult] = {}

        for rank, result in enumerate(dense_results):
            rrf_score = self._alpha * (1.0 / (RRF_K + rank + 1))
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + rrf_score
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result

        for rank, result in enumerate(sparse_results):
            rrf_score = (1.0 - self._alpha) * (1.0 / (RRF_K + rank + 1))
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + rrf_score
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result

        sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)

        return [
            RetrievalResult(
                chunk_id=cid,
                text=result_map[cid].text,
                score=scores[cid],
                source_document=result_map[cid].source_document,
                metadata=result_map[cid].metadata,
            )
            for cid in sorted_ids[:top_k]
        ]

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Index chunks into the sparse index (dense indexing is separate)."""
        return self._sparse.index(chunks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_hybrid_retriever.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/retrieval/hybrid.py packages/core/tests/test_hybrid_retriever.py
git commit -m "feat(core): add HybridRetriever with RRF fusion"
```

---

## Task 7: ContextualEnricher

**Files:**
- Create: `packages/core/src/rag_forge_core/context/enricher.py`
- Test: `packages/core/tests/test_enricher.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_enricher.py`:

```python
"""Tests for contextual enrichment (document summary prepending)."""

from rag_forge_core.chunking.base import Chunk
from rag_forge_core.context.enricher import ContextualEnricher, EnrichmentResult
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.parsing.base import Document


def _sample_document() -> Document:
    return Document(
        text="Python is a versatile programming language used for web development, "
        "data science, machine learning, and automation. It was created by "
        "Guido van Rossum and first released in 1991.",
        source_path="docs/python.md",
        metadata={"title": "Python Overview"},
    )


def _sample_chunks(source: str = "docs/python.md") -> list[Chunk]:
    return [
        Chunk(
            text="Python is a versatile programming language used for web development.",
            chunk_index=0,
            source_document=source,
            strategy_used="recursive",
        ),
        Chunk(
            text="It was created by Guido van Rossum and first released in 1991.",
            chunk_index=1,
            source_document=source,
            strategy_used="recursive",
        ),
    ]


class TestContextualEnricher:
    def test_enrich_returns_same_count(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        assert len(enriched) == len(chunks)

    def test_enriched_text_contains_original(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for original, result in zip(chunks, enriched, strict=True):
            assert original.text in result.text

    def test_enriched_text_has_context_prefix(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for chunk in enriched:
            assert chunk.text.startswith("[Document context:")

    def test_original_text_preserved_in_metadata(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for original, result in zip(chunks, enriched, strict=True):
            assert result.metadata is not None
            assert result.metadata["original_text"] == original.text

    def test_summary_stored_in_metadata(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for chunk in enriched:
            assert chunk.metadata is not None
            assert "document_summary" in chunk.metadata
            assert isinstance(chunk.metadata["document_summary"], str)
            assert len(str(chunk.metadata["document_summary"])) > 0

    def test_chunk_index_preserved(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        chunks = _sample_chunks()
        enriched = enricher.enrich(doc, chunks)
        for original, result in zip(chunks, enriched, strict=True):
            assert result.chunk_index == original.chunk_index
            assert result.source_document == original.source_document
            assert result.strategy_used == original.strategy_used

    def test_empty_chunks_returns_empty(self) -> None:
        enricher = ContextualEnricher(generator=MockGenerator())
        doc = _sample_document()
        enriched = enricher.enrich(doc, [])
        assert enriched == []

    def test_summary_called_once_per_document(self) -> None:
        """The generator should be called exactly once per enrich() call."""
        call_count = 0
        original_generate = MockGenerator.generate

        def counting_generate(self_gen: MockGenerator, system: str, user: str) -> str:
            nonlocal call_count
            call_count += 1
            return original_generate(self_gen, system, user)

        generator = MockGenerator()
        generator.generate = counting_generate.__get__(generator, MockGenerator)  # type: ignore[assignment]
        enricher = ContextualEnricher(generator=generator)
        doc = _sample_document()
        chunks = _sample_chunks()
        enricher.enrich(doc, chunks)
        assert call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_enricher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag_forge_core.context.enricher'`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/context/enricher.py`:

```python
"""Contextual enrichment: prepend document summaries to chunks before embedding.

Implements the Anthropic contextual retrieval technique. A short summary of the
entire document is generated via an LLM, then prepended to each chunk's text.
This gives the embedding model document-level context, improving retrieval
accuracy by 2-18% (per Anthropic research).
"""

from dataclasses import dataclass

from rag_forge_core.chunking.base import Chunk
from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.parsing.base import Document

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

        summary = self._generate_summary(document)

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_enricher.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/context/enricher.py packages/core/tests/test_enricher.py
git commit -m "feat(core): add ContextualEnricher for document summary prepending"
```

---

## Task 8: Update Module Exports

**Files:**
- Modify: `packages/core/src/rag_forge_core/retrieval/__init__.py`
- Modify: `packages/core/src/rag_forge_core/context/__init__.py`

- [ ] **Step 1: Update retrieval __init__.py**

Replace the full contents of `packages/core/src/rag_forge_core/retrieval/__init__.py`:

```python
"""Retrieval engine: dense, sparse, hybrid, and reranking."""

from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.config import RerankerType, RetrievalConfig, RetrievalStrategy
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import (
    BGELocalReranker,
    CohereReranker,
    MockReranker,
    RerankerProtocol,
)
from rag_forge_core.retrieval.sparse import SparseRetriever

__all__ = [
    "RetrievalResult",
    "RetrieverProtocol",
    "RetrievalConfig",
    "RetrievalStrategy",
    "RerankerType",
    "DenseRetriever",
    "SparseRetriever",
    "HybridRetriever",
    "RerankerProtocol",
    "CohereReranker",
    "BGELocalReranker",
    "MockReranker",
]
```

- [ ] **Step 2: Update context __init__.py**

Replace the full contents of `packages/core/src/rag_forge_core/context/__init__.py`:

```python
"""Context management: window tracking, enrichment, and caching."""

from rag_forge_core.context.enricher import ContextualEnricher, EnrichmentResult
from rag_forge_core.context.manager import ContextManager, ContextWindow

__all__ = ["ContextManager", "ContextWindow", "ContextualEnricher", "EnrichmentResult"]
```

- [ ] **Step 3: Verify imports work**

Run: `cd packages/core && uv run python -c "from rag_forge_core.retrieval import HybridRetriever, MockReranker, RetrievalConfig; from rag_forge_core.context import ContextualEnricher; print('All imports OK')"`
Expected: `All imports OK`

- [ ] **Step 4: Commit**

```bash
git add packages/core/src/rag_forge_core/retrieval/__init__.py packages/core/src/rag_forge_core/context/__init__.py
git commit -m "chore(core): update retrieval and context module exports"
```

---

## Task 9: Update IngestionPipeline

**Files:**
- Modify: `packages/core/src/rag_forge_core/ingestion/pipeline.py`

- [ ] **Step 1: Update IngestionPipeline with enricher and sparse indexing**

Replace the full contents of `packages/core/src/rag_forge_core/ingestion/pipeline.py`:

```python
"""Full ingestion pipeline: parse -> chunk -> [enrich] -> embed -> store [+ sparse index]."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

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
    ) -> None:
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.store = store
        self.collection_name = collection_name
        self.enricher = enricher
        self.sparse_retriever = sparse_retriever

    def run(self, source_path: str | Path) -> IngestionResult:
        """Run the full ingestion pipeline on a directory of documents."""
        source = Path(source_path)
        errors: list[str] = []
        enrichment_summaries = 0

        # 1. Parse documents
        documents, parse_errors = self.parser.parse_directory(source)
        errors.extend(parse_errors)

        if not documents:
            return IngestionResult(
                documents_processed=0, chunks_created=0, chunks_indexed=0, errors=errors
            )

        # 2. Chunk documents (and optionally enrich per document)
        all_chunks: list[Chunk] = []
        for doc in documents:
            chunks = self.chunker.chunk(doc.text, doc.source_path)

            # 3. Enrich (optional): prepend document summary to each chunk
            if self.enricher is not None and chunks:
                chunks = self.enricher.enrich(doc, chunks)
                enrichment_summaries += 1

            all_chunks.extend(chunks)

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
        for i in range(0, len(chunk_texts), EMBEDDING_BATCH_SIZE):
            batch = chunk_texts[i : i + EMBEDDING_BATCH_SIZE]
            vectors = self.embedder.embed(batch)
            all_vectors.extend(vectors)

        # 5. Create collection and upsert to vector store
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

        # 6. Sparse index (optional): build BM25 index
        if self.sparse_retriever is not None:
            sparse_chunks = [
                {"id": item.id, "text": item.text}
                for item in items
            ]
            self.sparse_retriever.index(sparse_chunks)

        return IngestionResult(
            documents_processed=len(documents),
            chunks_created=len(all_chunks),
            chunks_indexed=indexed_count,
            enrichment_summaries=enrichment_summaries,
            errors=errors,
        )
```

- [ ] **Step 2: Run existing pipeline integration tests to verify backward compatibility**

Run: `cd packages/core && uv run pytest tests/test_pipeline_integration.py -v`
Expected: All existing tests PASS (the new parameters are optional, so nothing breaks).

- [ ] **Step 3: Commit**

```bash
git add packages/core/src/rag_forge_core/ingestion/pipeline.py
git commit -m "feat(core): add enrichment and sparse indexing stages to IngestionPipeline"
```

---

## Task 10: Update QueryEngine

**Files:**
- Modify: `packages/core/src/rag_forge_core/query/engine.py`
- Modify: `packages/core/tests/test_query.py` (if it exists — add backward compat test)

- [ ] **Step 1: Update QueryEngine to accept RetrieverProtocol**

Replace the full contents of `packages/core/src/rag_forge_core/query/engine.py`:

```python
"""RAG query engine: retrieve relevant chunks → generate answer."""

from dataclasses import dataclass

from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol

_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based ONLY on the "
    "provided context. If the context does not contain enough information to answer "
    "the question, say so clearly. Do not make up information."
)


@dataclass
class QueryResult:
    """Result of a RAG query."""

    answer: str
    sources: list[RetrievalResult]
    model_used: str
    chunks_retrieved: int


class QueryEngine:
    """Executes RAG queries using any RetrieverProtocol implementation."""

    def __init__(
        self,
        retriever: RetrieverProtocol,
        generator: GenerationProvider,
        top_k: int = 5,
    ) -> None:
        self._retriever = retriever
        self._generator = generator
        self._top_k = top_k

    def query(self, question: str) -> QueryResult:
        """Execute a RAG query and return the generated answer with sources."""
        results = self._retriever.retrieve(question, self._top_k)

        if not results:
            return QueryResult(
                answer="No relevant context found for your question. Please index documents first.",
                sources=[],
                model_used=self._generator.model_name(),
                chunks_retrieved=0,
            )

        context_text = "\n\n".join(
            f"[Source {i + 1}]: {r.text}" for i, r in enumerate(results)
        )
        user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
        answer = self._generator.generate(_SYSTEM_PROMPT, user_prompt)

        return QueryResult(
            answer=answer,
            sources=results,
            model_used=self._generator.model_name(),
            chunks_retrieved=len(results),
        )
```

- [ ] **Step 2: Run existing query tests**

Run: `cd packages/core && uv run pytest tests/test_query.py -v`
Expected: Tests will FAIL because the constructor signature changed. The existing tests pass `embedder` + `store` directly.

- [ ] **Step 3: Update existing query tests for new interface**

Read `packages/core/tests/test_query.py` and update the test setup. Wherever `QueryEngine(embedder=..., store=..., generator=...)` is used, change to `QueryEngine(retriever=DenseRetriever(embedder=embedder, store=store, collection_name=collection), generator=generator)`. The `collection_name` parameter moves from `QueryEngine` to `DenseRetriever`.

Add this import at the top of the test file:
```python
from rag_forge_core.retrieval.dense import DenseRetriever
```

For each test that constructs `QueryEngine`, change:
```python
# Old:
engine = QueryEngine(
    embedder=embedder,
    store=store,
    generator=generator,
    collection_name="test",
    top_k=5,
)

# New:
retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test")
engine = QueryEngine(retriever=retriever, generator=generator, top_k=5)
```

- [ ] **Step 4: Run updated query tests**

Run: `cd packages/core && uv run pytest tests/test_query.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/query/engine.py packages/core/tests/test_query.py
git commit -m "refactor(core): QueryEngine accepts RetrieverProtocol instead of VectorStore"
```

---

## Task 11: Update Python CLI Entry Point

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py`

- [ ] **Step 1: Update cli.py with retrieval and enrichment args**

Replace the full contents of `packages/core/src/rag_forge_core/cli.py`:

```python
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


def _create_reranker(reranker_type: str, cohere_api_key: str | None = None):  # noqa: ANN201
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
        # Use a generation provider for summaries (default: same as --generator or mock)
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
```

- [ ] **Step 2: Verify the CLI entry point loads correctly**

Run: `cd packages/core && uv run python -m rag_forge_core.cli --help`
Expected: Help output showing `index` and `query` subcommands.

Run: `cd packages/core && uv run python -m rag_forge_core.cli index --help`
Expected: Help output showing `--enrich`, `--sparse-index-path`, `--enrichment-generator` flags.

Run: `cd packages/core && uv run python -m rag_forge_core.cli query --help`
Expected: Help output showing `--strategy`, `--alpha`, `--reranker`, `--sparse-index-path` flags.

- [ ] **Step 3: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py
git commit -m "feat(core): add retrieval and enrichment args to Python CLI bridge"
```

---

## Task 12: Update TypeScript CLI Commands

**Files:**
- Modify: `packages/cli/src/commands/index.ts`
- Modify: `packages/cli/src/commands/query.ts`

- [ ] **Step 1: Update index.ts with new flags**

Replace the full contents of `packages/cli/src/commands/index.ts`:

```typescript
import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface IndexResult {
  success: boolean;
  documents_processed: number;
  chunks_created: number;
  chunks_indexed: number;
  enrichment_summaries: number;
  errors: string[];
}

export function registerIndexCommand(program: Command): void {
  program
    .command("index")
    .requiredOption("-s, --source <dir>", "Source directory of documents to index")
    .option("-c, --collection <name>", "Collection name", "rag-forge")
    .option("-e, --embedding <provider>", "Embedding provider: openai | local | mock", "mock")
    .option("--strategy <name>", "Chunking strategy", "recursive")
    .option("--enrich", "Enable contextual enrichment (document summary prepending)")
    .option(
      "--sparse-index-path <path>",
      "Path to persist BM25 sparse index",
    )
    .option(
      "--enrichment-generator <provider>",
      "Generator for enrichment summaries: claude | openai | mock",
    )
    .description("Index documents into the vector store")
    .action(
      async (options: {
        source: string;
        collection: string;
        embedding: string;
        strategy: string;
        enrich?: boolean;
        sparseIndexPath?: string;
        enrichmentGenerator?: string;
      }) => {
        const spinner = ora("Indexing documents...").start();

        try {
          const configJson = JSON.stringify({
            embedding_provider: options.embedding,
            collection_name: options.collection,
            chunk_size: 512,
            overlap_ratio: 0.1,
          });

          const args = [
            "index",
            "--source",
            options.source,
            "--collection",
            options.collection,
            "--embedding",
            options.embedding,
            "--config-json",
            configJson,
          ];

          if (options.enrich) {
            args.push("--enrich");
          }
          if (options.sparseIndexPath) {
            args.push("--sparse-index-path", options.sparseIndexPath);
          }
          if (options.enrichmentGenerator) {
            args.push("--enrichment-generator", options.enrichmentGenerator);
          }

          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args,
          });

          if (result.exitCode !== 0) {
            spinner.fail("Indexing failed");
            logger.error(result.stderr || "Unknown error during indexing");
            process.exit(1);
          }

          const output: IndexResult = JSON.parse(result.stdout);

          if (output.success) {
            spinner.succeed("Indexing complete");
            logger.info(`Documents processed: ${String(output.documents_processed)}`);
            logger.info(`Chunks created: ${String(output.chunks_created)}`);
            logger.info(`Chunks indexed: ${String(output.chunks_indexed)}`);
            if (output.enrichment_summaries > 0) {
              logger.info(
                `Documents enriched: ${String(output.enrichment_summaries)}`,
              );
            }
          } else {
            spinner.warn("Indexing completed with errors");
            for (const error of output.errors) {
              logger.error(error);
            }
            process.exit(1);
          }
        } catch (error) {
          spinner.fail("Indexing failed");
          const message = error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
```

- [ ] **Step 2: Update query.ts with new flags**

Replace the full contents of `packages/cli/src/commands/query.ts`:

```typescript
import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface QuerySource {
  text: string;
  score: number;
  id: string;
  source_document?: string;
}

interface QueryResult {
  answer: string;
  model_used: string;
  chunks_retrieved: number;
  sources: QuerySource[];
}

export function registerQueryCommand(program: Command): void {
  program
    .command("query")
    .argument("<question>", "The question to ask the RAG pipeline")
    .option("-k, --top-k <number>", "Number of chunks to retrieve", "5")
    .option("-e, --embedding <provider>", "Embedding provider: openai | local | mock", "mock")
    .option("-g, --generator <provider>", "Generation provider: claude | openai | mock", "mock")
    .option("-c, --collection <name>", "Collection name", "rag-forge")
    .option(
      "--strategy <type>",
      "Retrieval strategy: dense | sparse | hybrid",
      "dense",
    )
    .option(
      "--alpha <number>",
      "RRF alpha weighting for hybrid retrieval (0.0-1.0)",
      "0.6",
    )
    .option(
      "--reranker <type>",
      "Reranker: none | cohere | bge-local",
      "none",
    )
    .option(
      "--sparse-index-path <path>",
      "Path to BM25 sparse index",
    )
    .description("Execute a RAG query against the indexed pipeline")
    .action(
      async (
        question: string,
        options: {
          topK: string;
          embedding: string;
          generator: string;
          collection: string;
          strategy: string;
          alpha: string;
          reranker: string;
          sparseIndexPath?: string;
        },
      ) => {
        const spinner = ora("Querying pipeline...").start();

        try {
          const args = [
            "query",
            "--question",
            question,
            "--embedding",
            options.embedding,
            "--generator",
            options.generator,
            "--collection",
            options.collection,
            "--top-k",
            options.topK,
            "--strategy",
            options.strategy,
            "--alpha",
            options.alpha,
            "--reranker",
            options.reranker,
          ];

          if (options.sparseIndexPath) {
            args.push("--sparse-index-path", options.sparseIndexPath);
          }

          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args,
          });

          if (result.exitCode !== 0) {
            spinner.fail("Query failed");
            logger.error(result.stderr || "Unknown error");
            process.exit(1);
          }

          const output: QueryResult = JSON.parse(result.stdout);
          spinner.succeed(`Answer (${output.model_used}):`);

          console.log("");
          console.log(output.answer);
          console.log("");

          if (output.sources.length > 0) {
            logger.info(`Sources (${String(output.chunks_retrieved)} chunks):`);
            for (const source of output.sources) {
              logger.info(
                `  [${source.score.toFixed(3)}] ${source.text.slice(0, 120)}...`,
              );
            }
          }
        } catch (error) {
          spinner.fail("Query failed");
          const message = error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
```

- [ ] **Step 3: Build TypeScript CLI**

Run: `cd packages/cli && pnpm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 4: Verify TypeScript type check passes**

Run: `cd packages/cli && pnpm run typecheck` (or `npx tsc --noEmit`)
Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/index.ts packages/cli/src/commands/query.ts
git commit -m "feat(cli): add --strategy, --alpha, --reranker, --enrich flags to CLI commands"
```

---

## Task 13: Integration Test — End-to-End Hybrid Pipeline

**Files:**
- Create: `packages/core/tests/test_hybrid_pipeline_integration.py`

- [ ] **Step 1: Write the integration test**

Create `packages/core/tests/test_hybrid_pipeline_integration.py`:

```python
"""End-to-end integration test: index with enrichment → query with hybrid retrieval."""

import tempfile
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.context.enricher import ContextualEnricher
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.engine import QueryEngine
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import MockReranker
from rag_forge_core.retrieval.sparse import SparseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


def _create_test_docs(tmp_path: Path) -> None:
    """Create test markdown files for indexing."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    (docs_dir / "python.md").write_text(
        "# Python\n\nPython is a versatile programming language. "
        "It is widely used for data science and machine learning. "
        "Python has a rich ecosystem of libraries including NumPy and pandas.",
        encoding="utf-8",
    )

    (docs_dir / "rust.md").write_text(
        "# Rust\n\nRust is a systems programming language focused on safety. "
        "It provides memory safety without garbage collection. "
        "Rust is commonly used for performance-critical applications.",
        encoding="utf-8",
    )

    (docs_dir / "javascript.md").write_text(
        "# JavaScript\n\nJavaScript powers interactive web applications. "
        "It runs in browsers and on servers via Node.js. "
        "TypeScript adds static typing to JavaScript.",
        encoding="utf-8",
    )


class TestHybridPipelineIntegration:
    def test_index_and_query_with_dense_only(self) -> None:
        """Baseline: index and query using dense-only retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            _create_test_docs(tmp_path)

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test",
            )
            result = pipeline.run(tmp_path / "docs")
            assert result.documents_processed == 3
            assert result.chunks_created > 0
            assert result.enrichment_summaries == 0

            retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test")
            engine = QueryEngine(retriever=retriever, generator=MockGenerator())
            query_result = engine.query("What is Python?")
            assert query_result.chunks_retrieved > 0
            assert len(query_result.answer) > 0

    def test_index_with_enrichment_and_sparse(self) -> None:
        """Index with contextual enrichment and sparse index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            _create_test_docs(tmp_path)
            sparse_path = str(tmp_path / "bm25-index")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            sparse = SparseRetriever(index_path=sparse_path)
            enricher = ContextualEnricher(generator=MockGenerator())

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test",
                enricher=enricher,
                sparse_retriever=sparse,
            )
            result = pipeline.run(tmp_path / "docs")
            assert result.documents_processed == 3
            assert result.chunks_created > 0
            assert result.enrichment_summaries == 3

            # Verify sparse index was persisted
            assert Path(sparse_path).exists()

    def test_hybrid_query_returns_results(self) -> None:
        """Full hybrid pipeline: index with enrichment → query with hybrid retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            _create_test_docs(tmp_path)
            sparse_path = str(tmp_path / "bm25-index")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            sparse = SparseRetriever(index_path=sparse_path)
            enricher = ContextualEnricher(generator=MockGenerator())

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test",
                enricher=enricher,
                sparse_retriever=sparse,
            )
            pipeline.run(tmp_path / "docs")

            # Query with hybrid retrieval
            dense = DenseRetriever(embedder=embedder, store=store, collection_name="test")
            loaded_sparse = SparseRetriever(index_path=sparse_path)
            hybrid = HybridRetriever(dense=dense, sparse=loaded_sparse, alpha=0.6)

            engine = QueryEngine(retriever=hybrid, generator=MockGenerator())
            result = engine.query("What is Python used for?")
            assert result.chunks_retrieved > 0
            assert len(result.answer) > 0

    def test_hybrid_query_with_reranker(self) -> None:
        """Full pipeline with reranker applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            _create_test_docs(tmp_path)
            sparse_path = str(tmp_path / "bm25-index")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            sparse = SparseRetriever(index_path=sparse_path)

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test",
                sparse_retriever=sparse,
            )
            pipeline.run(tmp_path / "docs")

            dense = DenseRetriever(embedder=embedder, store=store, collection_name="test")
            loaded_sparse = SparseRetriever(index_path=sparse_path)
            reranker = MockReranker()
            hybrid = HybridRetriever(
                dense=dense, sparse=loaded_sparse, alpha=0.6, reranker=reranker
            )

            engine = QueryEngine(retriever=hybrid, generator=MockGenerator())
            result = engine.query("Rust memory safety")
            assert result.chunks_retrieved > 0
```

- [ ] **Step 2: Run the integration test**

Run: `cd packages/core && uv run pytest tests/test_hybrid_pipeline_integration.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/core/tests/test_hybrid_pipeline_integration.py
git commit -m "test(core): add end-to-end hybrid pipeline integration tests"
```

---

## Task 14: Run Full Test Suite and Lint

- [ ] **Step 1: Run all Python tests**

Run: `cd packages/core && uv run pytest -v`
Expected: All tests PASS (existing + new).

- [ ] **Step 2: Run Python linter**

Run: `cd packages/core && uv run ruff check src/ tests/`
Expected: No lint errors. If there are errors, fix them.

- [ ] **Step 3: Run Python type checker**

Run: `cd packages/core && uv run mypy src/`
Expected: No type errors. If there are errors, fix them.

- [ ] **Step 4: Build TypeScript packages**

Run: `pnpm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Run TypeScript linter**

Run: `pnpm run lint`
Expected: No lint errors.

- [ ] **Step 6: Run TypeScript type check**

Run: `pnpm run typecheck`
Expected: No type errors.

- [ ] **Step 7: Fix any issues found in steps 1-6, then commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors from Phase 2A implementation"
```

- [ ] **Step 8: Run full test suite one final time**

Run: `pnpm run test`
Expected: All tests pass across both TypeScript and Python.
