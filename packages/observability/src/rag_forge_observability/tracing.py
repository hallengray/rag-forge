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
