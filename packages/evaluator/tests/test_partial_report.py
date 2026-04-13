"""Partial audit-report.json must be written when the loop aborts mid-run.

Guards the v0.1.3 resilience fix: a crash, Ctrl+C, or retry-budget-exhausted
error during the scoring loop must not vaporize the samples that already
finished. These tests fake a mid-loop exception and verify:

1. ``audit-report.partial.json`` exists with ``partial: true``.
2. ``metrics`` and ``rmm_level`` are unconditionally ``null`` at the top
   level (screenshot-safety: the standard shape visibly lacks data).
3. ``partial_metrics.by_metric`` carries subset aggregates with a caveat.
4. The orchestrator raises ``PartialAuditError`` wrapping the original
   exception, pointing at the written file.
5. Ctrl+C (``KeyboardInterrupt``) gets the same treatment as Exception.
6. When zero samples scored before the crash, no partial report is written
   (no signal to preserve) and the original exception propagates unchanged.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from rag_forge_evaluator.audit import (
    AuditConfig,
    AuditOrchestrator,
    PartialAuditError,
)
from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.metrics.base import MetricEvaluator


class _CountingExploder(MetricEvaluator):
    """A metric that returns real scores for the first N samples, then raises."""

    def __init__(self, name: str, explode_after: int) -> None:
        self._name = name
        self._explode_after = explode_after
        self._calls = 0

    def name(self) -> str:
        return self._name

    def default_threshold(self) -> float:
        return 0.85

    def evaluate_sample(self, sample: EvaluationSample, judge) -> MetricResult:
        self._calls += 1
        # The loop calls 1 metric per sample (this metric only); explode
        # after N samples have been fully scored.
        if self._calls > self._explode_after:
            raise RuntimeError("simulated mid-loop failure")
        return MetricResult(
            name=self._name, score=0.9, threshold=0.85, passed=True, skipped=False,
        )


def _make_config(tmp_path: Path) -> AuditConfig:
    jsonl = tmp_path / "telemetry.jsonl"
    samples = [
        {"query": f"q{i}", "contexts": ["ctx"], "response": f"r{i}"}
        for i in range(5)
    ]
    jsonl.write_text("\n".join(json.dumps(s) for s in samples), encoding="utf-8")
    return AuditConfig(
        input_path=jsonl,
        judge_model="mock",
        output_dir=tmp_path / "reports",
    )


def _patch_metrics_to_explode_after(explode_after: int) -> object:
    """Return a patch context that swaps the LLM-judge default metrics."""
    metrics = [
        _CountingExploder("faithfulness", explode_after),
        _CountingExploder("context_relevance", explode_after),
        _CountingExploder("answer_relevance", explode_after),
        _CountingExploder("hallucination", explode_after),
    ]
    return patch(
        "rag_forge_evaluator.metrics.llm_judge._default_metrics",
        return_value=metrics,
    )


def test_partial_report_written_on_mid_loop_exception(tmp_path: Path) -> None:
    config = _make_config(tmp_path)

    with _patch_metrics_to_explode_after(3), pytest.raises(PartialAuditError) as exc_info:
        AuditOrchestrator(config).run()

    partial_path = exc_info.value.partial_report_path
    assert partial_path.exists()
    assert partial_path.name == "audit-report.partial.json"

    data = json.loads(partial_path.read_text(encoding="utf-8"))
    assert data["partial"] is True
    assert data["completed_samples"] == 3
    assert data["total_samples"] == 5
    assert data["aborted_reason"] == "unhandled_exception"
    # Top-level full-run fields are null so screenshots of the standard shape
    # visibly lack data.
    assert data["metrics"] is None
    assert data["rmm_level"] is None
    assert data["rmm_name"] is None
    assert data["overall_score"] is None
    # Partial aggregates are namespaced with an in-band caveat.
    assert "partial_metrics" in data
    assert "note" in data["partial_metrics"]
    assert "NOT comparable" in data["partial_metrics"]["note"]
    assert "by_metric" in data["partial_metrics"]
    assert len(data["sample_results"]) == 3


def test_partial_audit_error_wraps_original(tmp_path: Path) -> None:
    config = _make_config(tmp_path)

    with _patch_metrics_to_explode_after(2), pytest.raises(PartialAuditError) as exc_info:
        AuditOrchestrator(config).run()

    assert isinstance(exc_info.value.original, RuntimeError)
    assert str(exc_info.value.original) == "simulated mid-loop failure"
    assert exc_info.value.completed_samples == 2
    assert exc_info.value.total_samples == 5


def test_keyboard_interrupt_also_writes_partial(tmp_path: Path) -> None:
    class _KeyboardInterrupter(MetricEvaluator):
        def __init__(self) -> None:
            self._calls = 0

        def name(self) -> str:
            return "faithfulness"

        def default_threshold(self) -> float:
            return 0.85

        def evaluate_sample(self, sample, judge):
            self._calls += 1
            if self._calls > 2:  # raise on the 3rd sample (after 2 complete)
                raise KeyboardInterrupt
            return MetricResult(
                name="faithfulness", score=0.9, threshold=0.85,
                passed=True, skipped=False,
            )

    metrics = [
        _KeyboardInterrupter(),
        _CountingExploder("context_relevance", 999),
        _CountingExploder("answer_relevance", 999),
        _CountingExploder("hallucination", 999),
    ]
    config = _make_config(tmp_path)

    with patch(
        "rag_forge_evaluator.metrics.llm_judge._default_metrics",
        return_value=metrics,
    ), pytest.raises(PartialAuditError) as exc_info:
        AuditOrchestrator(config).run()

    assert exc_info.value.aborted_reason == "keyboard_interrupt"
    assert exc_info.value.partial_report_path.exists()
    data = json.loads(exc_info.value.partial_report_path.read_text(encoding="utf-8"))
    assert data["aborted_reason"] == "keyboard_interrupt"


def test_no_partial_report_when_zero_samples_scored(tmp_path: Path) -> None:
    """If the first metric call explodes, there's no signal to preserve."""
    config = _make_config(tmp_path)

    with _patch_metrics_to_explode_after(0), pytest.raises(RuntimeError) as exc_info:
        AuditOrchestrator(config).run()

    # Original exception propagates — no PartialAuditError wrapper
    assert not isinstance(exc_info.value, PartialAuditError)
    assert "simulated mid-loop failure" in str(exc_info.value)
    assert not (tmp_path / "reports" / "audit-report.partial.json").exists()
