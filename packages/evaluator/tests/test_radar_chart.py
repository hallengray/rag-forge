"""Tests for radar chart SVG generation."""

from rag_forge_evaluator.engine import MetricResult
from rag_forge_evaluator.report.radar import generate_radar_svg


class TestRadarChart:
    def test_generates_svg(self) -> None:
        metrics = [
            MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
            MetricResult(name="context_relevance", score=0.82, threshold=0.80, passed=True),
            MetricResult(name="answer_relevance", score=0.78, threshold=0.80, passed=False),
            MetricResult(name="hallucination", score=0.95, threshold=0.95, passed=True),
        ]
        svg = generate_radar_svg(metrics)
        assert svg.startswith("<svg")
        assert "</svg>" in svg

    def test_contains_metric_labels(self) -> None:
        metrics = [
            MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
            MetricResult(name="context_relevance", score=0.82, threshold=0.80, passed=True),
        ]
        svg = generate_radar_svg(metrics)
        assert "faithfulness" in svg
        assert "context_relevance" in svg

    def test_contains_polygon(self) -> None:
        metrics = [
            MetricResult(name="a", score=0.5, threshold=0.5, passed=True),
            MetricResult(name="b", score=0.7, threshold=0.5, passed=True),
            MetricResult(name="c", score=0.9, threshold=0.5, passed=True),
        ]
        svg = generate_radar_svg(metrics)
        assert "polygon" in svg

    def test_empty_metrics(self) -> None:
        svg = generate_radar_svg([])
        assert "<svg" in svg
        assert "No metrics" in svg

    def test_single_metric(self) -> None:
        metrics = [MetricResult(name="only", score=0.8, threshold=0.5, passed=True)]
        svg = generate_radar_svg(metrics)
        assert "<svg" in svg
        assert "only" in svg
