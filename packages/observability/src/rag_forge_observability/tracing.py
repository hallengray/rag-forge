"""OpenTelemetry tracing instrumentation for RAG pipeline stages."""

from dataclasses import dataclass


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
    """Instruments RAG pipeline stages with OpenTelemetry spans.

    Every pipeline stage emits a span with standardized attributes:
    - Ingestion: latency, document count, chunk count
    - Embedding: token count, model, cost
    - Retrieval: recall@k, latency, chunk scores
    - Reranking: score distribution, nDCG improvement
    - Generation: token usage, latency, faithfulness
    """

    def __init__(self, service_name: str = "rag-forge") -> None:
        self.service_name = service_name
        self._enabled = False

    def enable(self) -> None:
        """Initialize OpenTelemetry tracing."""
        # Stub: full OTEL setup in Phase 3
        self._enabled = True

    def is_enabled(self) -> bool:
        """Check if tracing is active."""
        return self._enabled
