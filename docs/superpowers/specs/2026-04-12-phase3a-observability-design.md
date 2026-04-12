# Phase 3A: Observability (OpenTelemetry + Langfuse) Design Spec

## Context

RAG-Forge Phase 2 delivered the production pipeline (hybrid retrieval, security, evaluation, MCP server, templates). Phase 3A adds observability: OpenTelemetry tracing on all pipeline stages with OTLP export. Langfuse integration is achieved by pointing the OTLP exporter at Langfuse's OTEL-compatible endpoint — no Langfuse-specific code.

## Scope

**In scope:**
- Replace `TracingManager` stub with real OpenTelemetry SDK initialization
- Instrument `IngestionPipeline.run()` with per-stage spans (parse, chunk, enrich, embed, store, sparse_index)
- Instrument `QueryEngine.query()` with per-step spans (input_guard, retrieve, generate, output_guard)
- Instrument `AuditOrchestrator.run()` with evaluation span
- Activation via `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable (opt-in, no-op when unset)
- Standardized span attributes per stage (duration auto-captured, custom attributes for counts/models/scores)
- Add OpenTelemetry dependencies to `packages/observability/pyproject.toml`
- Update CLI entry points to initialize tracing when env var is set
- Unit tests for TracingManager and span emission

**Out of scope:** Drift detection (Phase 4), Grafana dashboard JSON (separate deliverable), custom OTEL metrics (counters/histograms — spans only for now), Langfuse SDK integration (OTEL exporter is sufficient).

## Architecture

The `TracingManager` checks for `OTEL_EXPORTER_OTLP_ENDPOINT` at initialization. If set, it configures a `TracerProvider` with `OTLPSpanExporter` and returns a real tracer. If not set, it returns the OpenTelemetry no-op tracer — zero overhead.

Pipeline code uses the standard OTEL context manager pattern:

```python
with tracer.start_as_current_span("rag-forge.parse") as span:
    span.set_attribute("document_count", len(docs))
    documents, errors = self.parser.parse_directory(source)
    span.set_attribute("error_count", len(errors))
```

Langfuse users configure: `OTEL_EXPORTER_OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel` plus `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`. The OTLP exporter sends spans to Langfuse with no Langfuse-specific code in RAG-Forge.

## Components

### 1. TracingManager (Replace Stub)

**Location:** `packages/observability/src/rag_forge_observability/tracing.py`

```python
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
        return self._enabled

    def get_tracer(self, name: str = "rag-forge") -> trace.Tracer:
        """Return a tracer instance. No-op tracer if tracing is not enabled."""
        return trace.get_tracer(name)

    def shutdown(self) -> None:
        """Flush pending spans and shut down the tracer provider."""
        if self._provider is not None:
            self._provider.shutdown()
```

`get_tracer()` always returns a valid tracer — if OTEL isn't initialized, it returns the global no-op tracer. This means pipeline code doesn't need `if tracing_enabled:` guards.

### 2. Instrumented IngestionPipeline

**Location:** `packages/core/src/rag_forge_core/ingestion/pipeline.py` (modify existing)

Changes:
1. Add optional `tracer: trace.Tracer | None = None` parameter to constructor.
2. In `run()`, if tracer is set, wrap each stage in a span. If tracer is None, execute as before (no tracing overhead).

Span structure:
```
rag-forge.ingest (parent)
  ├─ rag-forge.parse     {document_count, error_count}
  ├─ rag-forge.chunk     {chunk_count, strategy}
  ├─ rag-forge.enrich    {summaries_generated}        [if enricher set]
  ├─ rag-forge.embed     {chunk_count, model, batch_count}
  ├─ rag-forge.store     {chunks_indexed, collection}
  └─ rag-forge.sparse_index {chunk_count}             [if sparse set]
```

Implementation pattern — the tracer is optional. When absent, stages run without spans:

```python
from contextlib import contextmanager, nullcontext

def _span(self, name: str):
    """Return a span context manager, or nullcontext if no tracer."""
    if self._tracer is not None:
        return self._tracer.start_as_current_span(name)
    return nullcontext()
```

Then in `run()`:
```python
with self._span("rag-forge.ingest") as parent_span:
    # 1. Parse
    with self._span("rag-forge.parse") as span:
        documents, parse_errors = self.parser.parse_directory(source)
        if span is not None:
            span.set_attribute("document_count", len(documents))
            span.set_attribute("error_count", len(parse_errors))
    # ... etc
```

### 3. Instrumented QueryEngine

**Location:** `packages/core/src/rag_forge_core/query/engine.py` (modify existing)

Changes:
1. Add optional `tracer: trace.Tracer | None = None` parameter to constructor.
2. Wrap each step in a span.

Span structure:
```
rag-forge.query (parent)
  ├─ rag-forge.input_guard  {passed, blocked_by}      [if guard set]
  ├─ rag-forge.retrieve     {strategy, top_k, result_count}
  ├─ rag-forge.generate     {model}
  └─ rag-forge.output_guard {passed, faithfulness_score} [if guard set]
```

### 4. Instrumented AuditOrchestrator

**Location:** `packages/evaluator/src/rag_forge_evaluator/audit.py` (modify existing)

Changes:
1. Add optional `tracer: trace.Tracer | None = None` parameter to `AuditConfig`.
2. Wrap evaluation in a span.

Span structure:
```
rag-forge.audit (parent)
  ├─ rag-forge.load_input    {sample_count, source_type}
  ├─ rag-forge.evaluate      {engine, sample_count}
  ├─ rag-forge.score_rmm     {rmm_level}
  └─ rag-forge.generate_report {report_path}
```

### 5. CLI Integration

**Location:** `packages/core/src/rag_forge_core/cli.py` (modify existing)
**Location:** `packages/evaluator/src/rag_forge_evaluator/cli.py` (modify existing)

At the start of each CLI entry point (`cmd_index`, `cmd_query`, `cmd_status`, `cmd_audit`), initialize tracing:

```python
from rag_forge_observability.tracing import TracingManager

tracing = TracingManager()
tracing.enable()  # No-op if OTEL_EXPORTER_OTLP_ENDPOINT not set
tracer = tracing.get_tracer()
```

Pass `tracer` to the pipeline/engine constructors. Call `tracing.shutdown()` before exit to flush spans.

### 6. Updated Module Exports

**Location:** `packages/observability/src/rag_forge_observability/__init__.py`

Export `TracingManager`, `SpanAttributes`.

## Dependencies

### Updated: `packages/observability/pyproject.toml`

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "opentelemetry-api>=1.20",
    "opentelemetry-sdk>=1.20",
    "opentelemetry-exporter-otlp-proto-grpc>=1.20",
]
```

### Updated: `packages/core/pyproject.toml`

Add `rag-forge-observability` as a dependency so core can import the tracer.

Actually — to avoid a circular dependency (observability shouldn't depend on core, core shouldn't depend on observability), the `tracer` parameter should use the `opentelemetry.trace.Tracer` type directly. The core package only needs `opentelemetry-api` (lightweight, no SDK). The CLI entry points import from both packages.

```toml
# packages/core/pyproject.toml — add:
"opentelemetry-api>=1.20",
```

The full SDK + exporter stays in `packages/observability`. The core package only uses the API (tracer protocol, span interface).

## Testing Strategy

### Unit Tests

1. `test_tracing.py` (update existing) — Test `TracingManager` initializes when env var is set, returns no-op when not set, `shutdown()` works, `get_tracer()` always returns a tracer.

2. `test_instrumented_pipeline.py` — Test that `IngestionPipeline.run()` with a tracer emits the expected spans. Use OTEL's `InMemorySpanExporter` to capture spans in tests.

3. `test_instrumented_query.py` — Test that `QueryEngine.query()` with a tracer emits spans. Verify span names and attributes.

4. `test_instrumented_audit.py` — Test that `AuditOrchestrator.run()` with a tracer emits spans.

All tests use `InMemorySpanExporter` from `opentelemetry.sdk.trace.export.in_memory` — no real OTLP endpoint needed.

## File Summary

### New files:
- `packages/core/tests/test_instrumented_pipeline.py`
- `packages/core/tests/test_instrumented_query.py`
- `packages/evaluator/tests/test_instrumented_audit.py`

### Modified files:
- `packages/observability/pyproject.toml` (add OTEL deps)
- `packages/observability/src/rag_forge_observability/tracing.py` (replace stub)
- `packages/observability/src/rag_forge_observability/__init__.py` (exports)
- `packages/observability/tests/test_tracing.py` (update tests)
- `packages/core/pyproject.toml` (add opentelemetry-api)
- `packages/core/src/rag_forge_core/ingestion/pipeline.py` (add spans)
- `packages/core/src/rag_forge_core/query/engine.py` (add spans)
- `packages/core/src/rag_forge_core/cli.py` (initialize tracing)
- `packages/evaluator/src/rag_forge_evaluator/audit.py` (add spans)
- `packages/evaluator/src/rag_forge_evaluator/cli.py` (initialize tracing)
