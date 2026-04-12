"""Tests for JSON report output."""

import json
import tempfile

from rag_forge_evaluator.engine import EvaluationResult, MetricResult, SampleResult
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
