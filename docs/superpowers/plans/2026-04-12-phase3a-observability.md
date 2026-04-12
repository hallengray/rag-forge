# Phase 3A: Observability (OpenTelemetry + Langfuse) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenTelemetry tracing to all pipeline stages (ingest, query, audit) with OTLP export, activated via `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable. Langfuse works automatically as an OTEL-compatible endpoint.

**Architecture:** `TracingManager` initializes the OTEL SDK when the env var is set, providing a tracer instance. Pipeline code wraps stages in `with tracer.start_as_current_span()` context managers. When tracing is off, the OTEL no-op tracer is used — zero overhead. The core package only depends on `opentelemetry-api` (lightweight); the full SDK + exporter lives in the observability package.

**Tech Stack:** Python (opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp-proto-grpc), pytest with InMemorySpanExporter.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/core/tests/test_instrumented_pipeline.py` | Verify ingestion spans are emitted |
| `packages/core/tests/test_instrumented_query.py` | Verify query spans are emitted |
| `packages/evaluator/tests/test_instrumented_audit.py` | Verify audit spans are emitted |

### Modified Files

| File | Change |
|------|--------|
| `packages/observability/pyproject.toml` | Add OTEL dependencies |
| `packages/observability/src/rag_forge_observability/tracing.py` | Replace stub with real OTEL SDK init |
| `packages/observability/src/rag_forge_observability/__init__.py` | Export TracingManager, SpanAttributes |
| `packages/observability/tests/test_tracing.py` | Update tests for real TracingManager |
| `packages/core/pyproject.toml` | Add opentelemetry-api dependency |
| `packages/core/src/rag_forge_core/ingestion/pipeline.py` | Add optional tracer + spans |
| `packages/core/src/rag_forge_core/query/engine.py` | Add optional tracer + spans |
| `packages/core/src/rag_forge_core/cli.py` | Initialize tracing in CLI entry points |
| `packages/evaluator/src/rag_forge_evaluator/audit.py` | Add optional tracer + spans |
| `packages/evaluator/src/rag_forge_evaluator/cli.py` | Initialize tracing in audit CLI |

---

## Task 1: Add OpenTelemetry Dependencies

**Files:**
- Modify: `packages/observability/pyproject.toml`
- Modify: `packages/core/pyproject.toml`

- [ ] **Step 1: Update observability pyproject.toml**

Replace the full contents of `packages/observability/pyproject.toml`:

```toml
[project]
name = "rag-forge-observability"
version = "0.1.0"
description = "Observability stack: OpenTelemetry tracing, Langfuse integration, and drift detection"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "pydantic>=2.0",
    "opentelemetry-api>=1.20",
    "opentelemetry-sdk>=1.20",
    "opentelemetry-exporter-otlp-proto-grpc>=1.20",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/rag_forge_observability"]
```

- [ ] **Step 2: Update core pyproject.toml**

Add `"opentelemetry-api>=1.20"` to the dependencies list in `packages/core/pyproject.toml`. The existing deps are:

```toml
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
```

Add `"opentelemetry-api>=1.20",` to the end.

- [ ] **Step 3: Install dependencies**

Run: `uv sync --all-packages`

- [ ] **Step 4: Verify OTEL is importable**

Run: `uv run python -c "from opentelemetry import trace; print(trace.get_tracer('test'))"`

- [ ] **Step 5: Commit**

```bash
git add packages/observability/pyproject.toml packages/core/pyproject.toml
git commit -m "chore: add OpenTelemetry dependencies to observability and core packages"
```

---

## Task 2: Replace TracingManager Stub

**Files:**
- Modify: `packages/observability/src/rag_forge_observability/tracing.py`
- Modify: `packages/observability/src/rag_forge_observability/__init__.py`
- Modify: `packages/observability/tests/test_tracing.py`

- [ ] **Step 1: Write updated tests**

Replace the full contents of `packages/observability/tests/test_tracing.py`:

```python
"""Tests for TracingManager with OpenTelemetry."""

import os
from unittest.mock import patch

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter

from rag_forge_observability.tracing import TracingManager


class TestTracingManager:
    def test_default_disabled(self) -> None:
        manager = TracingManager()
        assert not manager.is_enabled()

    def test_enable_without_endpoint_stays_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
            manager = TracingManager()
            manager.enable()
            assert not manager.is_enabled()

    def test_enable_with_endpoint_enables(self) -> None:
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}):
            manager = TracingManager()
            manager.enable()
            assert manager.is_enabled()
            manager.shutdown()

    def test_custom_service_name(self) -> None:
        manager = TracingManager(service_name="my-rag-app")
        assert manager.service_name == "my-rag-app"

    def test_get_tracer_returns_tracer(self) -> None:
        manager = TracingManager()
        tracer = manager.get_tracer()
        assert isinstance(tracer, trace.Tracer)

    def test_get_tracer_when_disabled_returns_noop(self) -> None:
        manager = TracingManager()
        tracer = manager.get_tracer()
        # No-op tracer's spans should work without error
        with tracer.start_as_current_span("test") as span:
            assert span is not None

    def test_shutdown_without_enable(self) -> None:
        manager = TracingManager()
        manager.shutdown()  # Should not raise


class TestTracingWithInMemoryExporter:
    def test_spans_are_emitted(self) -> None:
        """Use InMemorySpanExporter to verify spans are created."""
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter

        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = provider.get_tracer("test")

        with tracer.start_as_current_span("test-span") as span:
            span.set_attribute("test.attr", "value")

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test-span"
        assert spans[0].attributes["test.attr"] == "value"
        provider.shutdown()
```

- [ ] **Step 2: Replace tracing.py**

Replace the full contents of `packages/observability/src/rag_forge_observability/tracing.py`:

```python
"""OpenTelemetry tracing instrumentation for RAG pipeline stages."""

import os
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


@dataclass
class SpanAttributes:
    """Standardized attributes for pipeline stage spans."""

    stage: str
    duration_ms: float | None = None
    token_count: int | None = None
    chunk_count: int | None = None
    model_used: str | None = None
    cost_usd: float | None = None


class TracingManager:
    """Initializes OpenTelemetry tracing based on environment configuration.

    Tracing activates when OTEL_EXPORTER_OTLP_ENDPOINT is set.
    When not set, returns the OTEL no-op tracer (zero overhead).

    Langfuse integration: set OTEL_EXPORTER_OTLP_ENDPOINT to
    https://cloud.langfuse.com/api/public/otel with LANGFUSE_PUBLIC_KEY
    and LANGFUSE_SECRET_KEY env vars.
    """

    def __init__(self, service_name: str = "rag-forge") -> None:
        self.service_name = service_name
        self._enabled = False
        self._provider: TracerProvider | None = None

    def enable(self) -> None:
        """Initialize OpenTelemetry tracing if OTLP endpoint is configured."""
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not endpoint:
            return

        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        resource = Resource.create({"service.name": self.service_name})
        self._provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        self._provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(self._provider)
        self._enabled = True

    def is_enabled(self) -> bool:
        """Check if tracing is active."""
        return self._enabled

    def get_tracer(self, name: str = "rag-forge") -> trace.Tracer:
        """Return a tracer instance. No-op tracer if tracing is not enabled."""
        return trace.get_tracer(name)

    def shutdown(self) -> None:
        """Flush pending spans and shut down the tracer provider."""
        if self._provider is not None:
            self._provider.shutdown()
```

- [ ] **Step 3: Update __init__.py**

Replace the full contents of `packages/observability/src/rag_forge_observability/__init__.py`:

```python
"""RAG-Forge Observability: OpenTelemetry tracing, Langfuse, and drift detection."""

from rag_forge_observability.tracing import SpanAttributes, TracingManager

__all__ = ["SpanAttributes", "TracingManager"]
```

- [ ] **Step 4: Run tests**

Run: `cd packages/observability && uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/observability/
git commit -m "feat(observability): replace TracingManager stub with real OpenTelemetry SDK"
```

---

## Task 3: Instrument IngestionPipeline

**Files:**
- Modify: `packages/core/src/rag_forge_core/ingestion/pipeline.py`
- Test: `packages/core/tests/test_instrumented_pipeline.py`

- [ ] **Step 1: Write the test**

Create `packages/core/tests/test_instrumented_pipeline.py`:

```python
"""Tests for instrumented IngestionPipeline with OpenTelemetry spans."""

import tempfile
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.storage.qdrant import QdrantStore


def _setup_tracer() -> tuple[InMemorySpanExporter, TracerProvider]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider


class TestInstrumentedPipeline:
    def test_emits_spans_when_tracer_set(self) -> None:
        exporter, provider = _setup_tracer()
        tracer = provider.get_tracer("test")

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello world.", encoding="utf-8")

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=MockEmbedder(dimension=384),
                store=QdrantStore(),
                collection_name="test-traced",
                tracer=tracer,
            )
            pipeline.run(docs)

        spans = exporter.get_finished_spans()
        span_names = [s.name for s in spans]
        assert "rag-forge.ingest" in span_names
        assert "rag-forge.parse" in span_names
        assert "rag-forge.chunk" in span_names
        assert "rag-forge.embed" in span_names
        assert "rag-forge.store" in span_names
        provider.shutdown()

    def test_span_attributes(self) -> None:
        exporter, provider = _setup_tracer()
        tracer = provider.get_tracer("test")

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello world.", encoding="utf-8")

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=MockEmbedder(dimension=384),
                store=QdrantStore(),
                collection_name="test-traced",
                tracer=tracer,
            )
            pipeline.run(docs)

        spans = exporter.get_finished_spans()
        parse_span = next(s for s in spans if s.name == "rag-forge.parse")
        assert "document_count" in parse_span.attributes
        provider.shutdown()

    def test_no_spans_without_tracer(self) -> None:
        exporter, provider = _setup_tracer()

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello.", encoding="utf-8")

            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=MockEmbedder(dimension=384),
                store=QdrantStore(),
            )
            pipeline.run(docs)

        spans = exporter.get_finished_spans()
        assert len(spans) == 0
        provider.shutdown()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core && uv run pytest tests/test_instrumented_pipeline.py -v`
Expected: FAIL — `IngestionPipeline` doesn't accept `tracer` parameter yet.

- [ ] **Step 3: Update IngestionPipeline**

Read the current `packages/core/src/rag_forge_core/ingestion/pipeline.py` and add:

1. Imports at the top:
```python
from contextlib import nullcontext
from typing import Any

from opentelemetry import trace
```

2. Add `tracer` parameter to `__init__`:
```python
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
        # ... existing assignments ...
        self._tracer = tracer
```

3. Add helper method:
```python
    def _span(self, name: str) -> Any:
        """Return a span context manager, or nullcontext if no tracer."""
        if self._tracer is not None:
            return self._tracer.start_as_current_span(name)
        return nullcontext()
```

4. Wrap each stage in `run()` with spans. The structure:

```python
    def run(self, source_path: str | Path) -> IngestionResult:
        source = Path(source_path)
        errors: list[str] = []
        enrichment_summaries = 0

        with self._span("rag-forge.ingest"):
            # 1. Parse
            with self._span("rag-forge.parse") as span:
                documents, parse_errors = self.parser.parse_directory(source)
                errors.extend(parse_errors)
                if span is not None:
                    span.set_attribute("document_count", len(documents))
                    span.set_attribute("error_count", len(parse_errors))

            if not documents:
                return IngestionResult(...)

            # 2. Chunk
            all_chunks: list[Chunk] = []
            with self._span("rag-forge.chunk") as span:
                for doc in documents:
                    chunks = self.chunker.chunk(doc.text, doc.source_path)
                    if self.enricher is not None and chunks:
                        # 3. Enrich inside chunk span (or separate)
                        chunks = self.enricher.enrich(doc, chunks)
                        enrichment_summaries += 1
                    all_chunks.extend(chunks)
                if span is not None:
                    span.set_attribute("chunk_count", len(all_chunks))
                    span.set_attribute("strategy", "recursive")

            if not all_chunks:
                return IngestionResult(...)

            # Enrich span (if enricher was used)
            if self.enricher is not None and enrichment_summaries > 0:
                with self._span("rag-forge.enrich") as span:
                    if span is not None:
                        span.set_attribute("summaries_generated", enrichment_summaries)

            # 4. Embed
            with self._span("rag-forge.embed") as span:
                chunk_texts = [c.text for c in all_chunks]
                all_vectors: list[list[float]] = []
                batch_count = 0
                for i in range(0, len(chunk_texts), EMBEDDING_BATCH_SIZE):
                    batch = chunk_texts[i : i + EMBEDDING_BATCH_SIZE]
                    vectors = self.embedder.embed(batch)
                    all_vectors.extend(vectors)
                    batch_count += 1
                if span is not None:
                    span.set_attribute("chunk_count", len(all_chunks))
                    span.set_attribute("model", self.embedder.model_name())
                    span.set_attribute("batch_count", batch_count)

            # 5. Store
            with self._span("rag-forge.store") as span:
                self.store.create_collection(self.collection_name, self.embedder.dimension())
                items = [...]  # same item construction as before
                indexed_count = self.store.upsert(self.collection_name, items)
                if span is not None:
                    span.set_attribute("chunks_indexed", indexed_count)
                    span.set_attribute("collection", self.collection_name)

            # 6. Sparse index
            if self.sparse_retriever is not None:
                with self._span("rag-forge.sparse_index") as span:
                    sparse_chunks = [...]  # same as before
                    self.sparse_retriever.index(sparse_chunks)
                    if span is not None:
                        span.set_attribute("chunk_count", len(sparse_chunks))

        return IngestionResult(...)
```

IMPORTANT: Keep all existing logic exactly the same. Only add the `with self._span(...)` wrappers and `span.set_attribute()` calls. Do NOT change the pipeline behavior.

- [ ] **Step 4: Run tests**

Run: `cd packages/core && uv run pytest tests/test_instrumented_pipeline.py tests/test_pipeline_integration.py -v`
Expected: All tests PASS (new + existing backward compat).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/ingestion/pipeline.py packages/core/tests/test_instrumented_pipeline.py
git commit -m "feat(core): instrument IngestionPipeline with OpenTelemetry spans"
```

---

## Task 4: Instrument QueryEngine

**Files:**
- Modify: `packages/core/src/rag_forge_core/query/engine.py`
- Test: `packages/core/tests/test_instrumented_query.py`

- [ ] **Step 1: Write the test**

Create `packages/core/tests/test_instrumented_query.py`:

```python
"""Tests for instrumented QueryEngine with OpenTelemetry spans."""

import tempfile
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.engine import QueryEngine
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


def _setup_tracer() -> tuple[InMemorySpanExporter, TracerProvider]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider


class TestInstrumentedQuery:
    def test_emits_spans_when_tracer_set(self) -> None:
        exporter, provider = _setup_tracer()
        tracer = provider.get_tracer("test")

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Python\n\nPython is a language.", encoding="utf-8")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test-query-traced",
            )
            pipeline.run(docs)

            retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-query-traced")
            engine = QueryEngine(retriever=retriever, generator=MockGenerator(), tracer=tracer)
            engine.query("What is Python?")

        spans = exporter.get_finished_spans()
        span_names = [s.name for s in spans]
        assert "rag-forge.query" in span_names
        assert "rag-forge.retrieve" in span_names
        assert "rag-forge.generate" in span_names
        provider.shutdown()

    def test_no_spans_without_tracer(self) -> None:
        exporter, provider = _setup_tracer()

        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello.", encoding="utf-8")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            pipeline = IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test-notrace",
            )
            pipeline.run(docs)

            retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-notrace")
            engine = QueryEngine(retriever=retriever, generator=MockGenerator())
            engine.query("Hello?")

        spans = exporter.get_finished_spans()
        assert len(spans) == 0
        provider.shutdown()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core && uv run pytest tests/test_instrumented_query.py -v`
Expected: FAIL — `QueryEngine` doesn't accept `tracer` yet.

- [ ] **Step 3: Update QueryEngine**

Read `packages/core/src/rag_forge_core/query/engine.py` and add:

1. Imports:
```python
from contextlib import nullcontext
from typing import Any

from opentelemetry import trace
```

2. Add `tracer` parameter to `__init__`:
```python
    def __init__(
        self,
        retriever: RetrieverProtocol,
        generator: GenerationProvider,
        top_k: int = 5,
        input_guard: InputGuard | None = None,
        output_guard: OutputGuard | None = None,
        tracer: trace.Tracer | None = None,
    ) -> None:
        # ... existing assignments ...
        self._tracer = tracer
```

3. Add helper:
```python
    def _span(self, name: str) -> Any:
        if self._tracer is not None:
            return self._tracer.start_as_current_span(name)
        return nullcontext()
```

4. Wrap `query()` steps in spans:
```python
    def query(self, question: str, alpha: float | None = None, user_id: str = "default") -> QueryResult:
        with self._span("rag-forge.query"):
            # 1. Input guard
            if self._input_guard is not None:
                with self._span("rag-forge.input_guard") as span:
                    guard_result = self._input_guard.check(question, user_id=user_id)
                    if span is not None:
                        span.set_attribute("passed", guard_result.passed)
                        if guard_result.blocked_by:
                            span.set_attribute("blocked_by", guard_result.blocked_by)
                    if not guard_result.passed:
                        return QueryResult(...)

            # 2. Retrieve
            with self._span("rag-forge.retrieve") as span:
                # ... existing retriever logic ...
                results = retriever.retrieve(question, self._top_k)
                if span is not None:
                    span.set_attribute("result_count", len(results))
                    span.set_attribute("top_k", self._top_k)

            if not results:
                return QueryResult(...)

            # 3. Generate
            with self._span("rag-forge.generate") as span:
                # ... existing generation logic ...
                answer = self._generator.generate(_SYSTEM_PROMPT, user_prompt)
                if span is not None:
                    span.set_attribute("model", self._generator.model_name())

            # 4. Output guard
            if self._output_guard is not None:
                with self._span("rag-forge.output_guard") as span:
                    # ... existing output guard logic ...
                    if span is not None:
                        span.set_attribute("passed", output_result.passed)
                        if output_result.faithfulness_score is not None:
                            span.set_attribute("faithfulness_score", output_result.faithfulness_score)

            return QueryResult(...)
```

IMPORTANT: Keep all existing logic exactly the same. Only add span wrappers and attributes.

- [ ] **Step 4: Run tests**

Run: `cd packages/core && uv run pytest tests/test_instrumented_query.py tests/test_query.py tests/test_security_integration.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/query/engine.py packages/core/tests/test_instrumented_query.py
git commit -m "feat(core): instrument QueryEngine with OpenTelemetry spans"
```

---

## Task 5: Instrument AuditOrchestrator

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/audit.py`
- Test: `packages/evaluator/tests/test_instrumented_audit.py`

- [ ] **Step 1: Write the test**

Create `packages/evaluator/tests/test_instrumented_audit.py`:

```python
"""Tests for instrumented AuditOrchestrator with OpenTelemetry spans."""

import json
import tempfile
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator


def _setup_tracer() -> tuple[InMemorySpanExporter, TracerProvider]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider


def _create_test_jsonl(path: Path) -> None:
    samples = [
        {"query": "What is Python?", "contexts": ["Python is a language."], "response": "Python is a language."},
    ]
    path.write_text("\n".join(json.dumps(s) for s in samples), encoding="utf-8")


class TestInstrumentedAudit:
    def test_emits_spans_when_tracer_set(self) -> None:
        exporter, provider = _setup_tracer()
        tracer = provider.get_tracer("test")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)

            config = AuditConfig(input_path=jsonl, output_dir=tmp / "reports", tracer=tracer)
            AuditOrchestrator(config).run()

        spans = exporter.get_finished_spans()
        span_names = [s.name for s in spans]
        assert "rag-forge.audit" in span_names
        assert "rag-forge.evaluate" in span_names
        provider.shutdown()

    def test_no_spans_without_tracer(self) -> None:
        exporter, provider = _setup_tracer()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)

            config = AuditConfig(input_path=jsonl, output_dir=tmp / "reports")
            AuditOrchestrator(config).run()

        spans = exporter.get_finished_spans()
        assert len(spans) == 0
        provider.shutdown()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/evaluator && uv run pytest tests/test_instrumented_audit.py -v`
Expected: FAIL — `AuditConfig` doesn't have `tracer` field yet.

- [ ] **Step 3: Update AuditOrchestrator**

Read `packages/evaluator/src/rag_forge_evaluator/audit.py` and add:

1. Imports:
```python
from contextlib import nullcontext
from typing import Any

from opentelemetry import trace
```

2. Add `tracer` to `AuditConfig`:
```python
@dataclass
class AuditConfig:
    input_path: Path | None = None
    golden_set_path: Path | None = None
    judge_model: str | None = None
    output_dir: Path = Path("./reports")
    generate_pdf: bool = False
    thresholds: dict[str, float] | None = None
    evaluator_engine: str = "llm-judge"
    tracer: trace.Tracer | None = None
```

3. Add `_span` helper to `AuditOrchestrator`:
```python
    def _span(self, name: str) -> Any:
        if self.config.tracer is not None:
            return self.config.tracer.start_as_current_span(name)
        return nullcontext()
```

4. Wrap `run()` steps:
```python
    def run(self) -> AuditReport:
        with self._span("rag-forge.audit"):
            # 1. Load input
            with self._span("rag-forge.load_input") as span:
                # ... existing load logic ...
                if span is not None:
                    span.set_attribute("sample_count", len(samples))
                    span.set_attribute("source_type", "jsonl" if self.config.input_path else "golden_set")

            # 2-3. Evaluate
            with self._span("rag-forge.evaluate") as span:
                evaluation = evaluator.evaluate(samples)
                if span is not None:
                    span.set_attribute("engine", self.config.evaluator_engine)
                    span.set_attribute("sample_count", len(samples))

            # 4. RMM
            with self._span("rag-forge.score_rmm") as span:
                metric_map = {m.name: m.score for m in evaluation.metrics}
                rmm_level = RMMScorer().assess(metric_map)
                if span is not None:
                    span.set_attribute("rmm_level", int(rmm_level))

            # 5-7. Report + history (existing code, wrapped in span)
            with self._span("rag-forge.generate_report") as span:
                # ... existing report generation ...
                if span is not None:
                    span.set_attribute("report_path", str(report_path))

        return AuditReport(...)
```

- [ ] **Step 4: Run tests**

Run: `cd packages/evaluator && uv run pytest tests/test_instrumented_audit.py tests/test_audit.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/audit.py packages/evaluator/tests/test_instrumented_audit.py
git commit -m "feat(evaluator): instrument AuditOrchestrator with OpenTelemetry spans"
```

---

## Task 6: CLI Tracing Initialization

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py`
- Modify: `packages/evaluator/src/rag_forge_evaluator/cli.py`

- [ ] **Step 1: Update core CLI**

Read `packages/core/src/rag_forge_core/cli.py`. Add at the top (after existing imports):

```python
from rag_forge_observability.tracing import TracingManager
```

In `cmd_index()`, after building the pipeline but before `pipeline.run()`, add tracing init:

```python
    tracing = TracingManager()
    tracing.enable()
    tracer = tracing.get_tracer()
```

Pass `tracer=tracer` to the `IngestionPipeline(...)` constructor.

Add `tracing.shutdown()` after `json.dump(output, sys.stdout)`.

Do the same in `cmd_query()` — init tracing, pass `tracer=tracer` to `QueryEngine(...)`, shutdown after output.

- [ ] **Step 2: Update evaluator CLI**

Read `packages/evaluator/src/rag_forge_evaluator/cli.py`. Add import:

```python
from rag_forge_observability.tracing import TracingManager
```

In `cmd_audit()`, init tracing and pass `tracer` to `AuditConfig`:

```python
    tracing = TracingManager()
    tracing.enable()
    tracer = tracing.get_tracer()

    config = AuditConfig(
        ...
        tracer=tracer,
    )

    report = AuditOrchestrator(config).run()

    # ... output json ...

    tracing.shutdown()
```

- [ ] **Step 3: Verify CLIs load**

Run: `cd packages/core && uv run python -m rag_forge_core.cli --help`
Run: `cd packages/evaluator && uv run python -m rag_forge_evaluator.cli --help`
Expected: Both show help without errors.

- [ ] **Step 4: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py packages/evaluator/src/rag_forge_evaluator/cli.py
git commit -m "feat(cli): initialize OpenTelemetry tracing in CLI entry points"
```

---

## Task 7: Run Full Test Suite and Lint

- [ ] **Step 1: Run all Python tests**

Run: `uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run Python linter**

Run: `uv run ruff check .`
Expected: No errors. Fix any.

- [ ] **Step 3: Run Python type checker**

Run: `uv run mypy packages/core/src packages/evaluator/src packages/observability/src`
Expected: No errors. Fix any. (May need to add `opentelemetry.*` to mypy ignore list if stubs are missing.)

- [ ] **Step 4: Build TypeScript**

Run: `pnpm run build`
Expected: Build succeeds.

- [ ] **Step 5: Run TypeScript lint and typecheck**

Run: `pnpm run lint && pnpm run typecheck`
Expected: No errors.

- [ ] **Step 6: Fix any issues, commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors from Phase 3A implementation"
```

- [ ] **Step 7: Push**

```bash
git push
```
