"""Tests for instrumented AuditOrchestrator with OpenTelemetry spans."""

import json
import tempfile
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator


def _setup_tracer():
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
