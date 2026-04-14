"""Tests for JSON report output."""

import json
import tempfile

import pytest

from rag_forge_evaluator.engine import (
    EvaluationResult,
    MetricResult,
    SampleResult,
    SkipRecord,
)
from rag_forge_evaluator.maturity import RMMLevel
from rag_forge_evaluator.report.generator import ReportGenerator


class TestJsonReport:
    def test_generates_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True)],
                overall_score=0.90, samples_evaluated=5, passed=True,
            )
            path = gen.generate_json(result, RMMLevel.TRUST)
            assert path.exists()
            assert path.suffix == ".json"

    def test_json_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[
                    MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
                    MetricResult(name="context_relevance", score=0.82, threshold=0.80, passed=True),
                ],
                overall_score=0.86, samples_evaluated=10, passed=True,
            )
            path = gen.generate_json(result, RMMLevel.TRUST)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "timestamp" in data
            assert data["overall_score"] == 0.86
            assert data["passed"] is True
            assert data["rmm_level"] == 3
            assert data["samples_evaluated"] == 10
            assert "faithfulness" in data["metrics"]
            assert data["metrics"]["faithfulness"]["score"] == 0.90

    def test_json_includes_worst_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            sample_results = [
                SampleResult(query="bad query", response="bad response", metrics={"faithfulness": 0.3}, worst_metric="faithfulness", root_cause="generation"),
            ]
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.3, threshold=0.85, passed=False)],
                overall_score=0.3, samples_evaluated=1, passed=False, sample_results=sample_results,
            )
            path = gen.generate_json(result, RMMLevel.NAIVE, sample_results=sample_results)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data["worst_samples"]) == 1
            assert data["worst_samples"][0]["root_cause"] == "generation"

    def test_json_report_includes_skipped_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.78, threshold=0.85, passed=False)],
                overall_score=0.74,
                samples_evaluated=12,
                passed=False,
                skipped_samples=[
                    SkipRecord(
                        sample_id="s2",
                        metric_name="faithfulness",
                        reason="timeout",
                        exception_type="TimeoutError",
                    ),
                ],
            )
            path = gen.generate_json(result, RMMLevel.NAIVE)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "skipped_samples" in data
            assert data["skipped_samples"] == [
                {
                    "sample_id": "s2",
                    "metric_name": "faithfulness",
                    "reason": "timeout",
                    "exception_type": "TimeoutError",
                }
            ]

    def test_json_report_includes_scoring_modes_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.78, threshold=0.85, passed=False)],
                overall_score=0.74,
                samples_evaluated=12,
                passed=False,
                scoring_modes_count={"standard": 11, "safety_refusal": 1},
            )
            path = gen.generate_json(result, RMMLevel.NAIVE)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "scoring_modes_count" in data
            assert data["scoring_modes_count"] == {"standard": 11, "safety_refusal": 1}

    def test_json_report_includes_safety_refusal_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.78, threshold=0.85, passed=False)],
                overall_score=0.74,
                samples_evaluated=12,
                passed=False,
                scoring_modes_count={"standard": 11, "safety_refusal": 1},
            )
            path = gen.generate_json(result, RMMLevel.NAIVE)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "safety_refusal_rate" in data
            assert data["safety_refusal_rate"] == pytest.approx(1 / 12)

    def test_json_report_per_sample_scoring_mode_and_justification(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            sample_results = [
                SampleResult(
                    query="q1",
                    response="r1",
                    metrics={"faithfulness": 0.8},
                    worst_metric="faithfulness",
                    root_cause="none",
                    sample_id="s1",
                    scoring_mode="safety_refusal",
                    refusal_justification="no paediatric dosing",
                )
            ]
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.78, threshold=0.85, passed=False)],
                overall_score=0.74,
                samples_evaluated=1,
                passed=False,
                sample_results=sample_results,
                scoring_modes_count={"safety_refusal": 1},
            )
            path = gen.generate_json(result, RMMLevel.NAIVE, sample_results=sample_results)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "sample_results" in data
            assert len(data["sample_results"]) > 0
            first = data["sample_results"][0]
            assert first["scoring_mode"] == "safety_refusal"
            assert first["refusal_justification"] == "no paediatric dosing"

    def test_json_report_empty_refusal_rate_zero_when_no_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            empty = EvaluationResult(metrics=[], overall_score=0.0, samples_evaluated=0, passed=False)
            path = gen.generate_json(empty, RMMLevel.NAIVE)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["safety_refusal_rate"] == 0.0
            assert data["skipped_samples"] == []
            assert data["scoring_modes_count"] == {}
