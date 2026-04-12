"""Tests for TracingManager with OpenTelemetry."""

import os
from unittest.mock import patch

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

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
        with tracer.start_as_current_span("test") as span:
            assert span is not None

    def test_shutdown_without_enable(self) -> None:
        manager = TracingManager()
        manager.shutdown()


class TestTracingWithInMemoryExporter:
    def test_spans_are_emitted(self) -> None:
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
