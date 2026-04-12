"""Tests for enhanced HTML report."""

import tempfile

from rag_forge_evaluator.engine import EvaluationResult, MetricResult, SampleResult
from rag_forge_evaluator.maturity import RMMLevel
from rag_forge_evaluator.report.generator import ReportGenerator


class TestEnhancedReport:
    def test_html_contains_radar_chart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[
                    MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
                    MetricResult(name="context_relevance", score=0.82, threshold=0.80, passed=True),
                ],
                overall_score=0.86, samples_evaluated=5, passed=True,
            )
            path = gen.generate_html(result, RMMLevel.TRUST)
            html = path.read_text(encoding="utf-8")
            assert "<svg" in html
            assert "polygon" in html

    def test_html_contains_trend_arrows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True)],
                overall_score=0.90, samples_evaluated=5, passed=True,
            )
            trends = {"faithfulness": "\u2191"}
            path = gen.generate_html(result, RMMLevel.TRUST, trends=trends)
            html = path.read_text(encoding="utf-8")
            assert "\u2191" in html

    def test_html_contains_per_sample_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            sample_results = [
                SampleResult(query="What is Python?", response="A language", metrics={"faithfulness": 0.90}, worst_metric="faithfulness", root_cause="none"),
            ]
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True)],
                overall_score=0.90, samples_evaluated=1, passed=True, sample_results=sample_results,
            )
            path = gen.generate_html(result, RMMLevel.TRUST, sample_results=sample_results)
            html = path.read_text(encoding="utf-8")
            assert "What is Python?" in html

    def test_html_no_trends_without_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True)],
                overall_score=0.90, samples_evaluated=5, passed=True,
            )
            path = gen.generate_html(result, RMMLevel.TRUST)
            html = path.read_text(encoding="utf-8")
            assert "\u2191" not in html
            assert "\u2193" not in html
