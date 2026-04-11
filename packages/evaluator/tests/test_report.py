"""Tests for the HTML report generator."""

from pathlib import Path

from rag_forge_evaluator.engine import EvaluationResult, MetricResult
from rag_forge_evaluator.maturity import RMMLevel
from rag_forge_evaluator.report.generator import ReportGenerator


def _mock_result() -> EvaluationResult:
    return EvaluationResult(
        metrics=[
            MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
            MetricResult(name="context_relevance", score=0.75, threshold=0.80, passed=False),
            MetricResult(name="answer_relevance", score=0.88, threshold=0.80, passed=True),
            MetricResult(name="hallucination", score=0.96, threshold=0.95, passed=True),
        ],
        overall_score=0.87,
        samples_evaluated=10,
        passed=False,
    )


class TestReportGenerator:
    def test_generates_html_file(self, tmp_path: Path) -> None:
        path = ReportGenerator(output_dir=tmp_path).generate_html(_mock_result(), RMMLevel.NAIVE)
        assert path.exists()
        assert path.suffix == ".html"

    def test_html_contains_rmm_badge(self, tmp_path: Path) -> None:
        path = ReportGenerator(output_dir=tmp_path).generate_html(_mock_result(), RMMLevel.TRUST)
        html = path.read_text(encoding="utf-8")
        assert "RMM-3" in html
        assert "Better Trust" in html

    def test_html_contains_metric_scores(self, tmp_path: Path) -> None:
        path = ReportGenerator(output_dir=tmp_path).generate_html(_mock_result(), RMMLevel.NAIVE)
        html = path.read_text(encoding="utf-8")
        assert "faithfulness" in html
        assert "PASS" in html
        assert "FAIL" in html

    def test_html_contains_overall_score(self, tmp_path: Path) -> None:
        path = ReportGenerator(output_dir=tmp_path).generate_html(_mock_result(), RMMLevel.NAIVE)
        html = path.read_text(encoding="utf-8")
        assert "0.87" in html

    def test_html_is_standalone(self, tmp_path: Path) -> None:
        path = ReportGenerator(output_dir=tmp_path).generate_html(_mock_result(), RMMLevel.NAIVE)
        html = path.read_text(encoding="utf-8")
        assert "<html" in html
        assert "<style" in html
        assert "RAG-Forge" in html
