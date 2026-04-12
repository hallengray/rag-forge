"""Tests for cost estimation."""

import pytest

from rag_forge_evaluator.cost import CostEstimator, CostReport, ModelPricing


class TestModelPricing:
    def test_default_pricing_includes_common_models(self) -> None:
        pricing = ModelPricing.defaults()
        assert "gpt-4o" in pricing.models
        assert "claude-sonnet-4-20250514" in pricing.models
        assert "text-embedding-3-large" in pricing.models

    def test_cost_per_token(self) -> None:
        pricing = ModelPricing.defaults()
        cost = pricing.cost_per_1k_input("text-embedding-3-large")
        assert cost > 0

    def test_unknown_model_returns_zero(self) -> None:
        pricing = ModelPricing.defaults()
        assert pricing.cost_per_1k_input("unknown-model-xyz") == 0.0


class TestCostEstimator:
    def test_estimate_from_telemetry(self) -> None:
        estimator = CostEstimator()
        telemetry = [
            {"model": "text-embedding-3-large", "input_tokens": 1000, "output_tokens": 0, "calls": 10},
            {"model": "claude-sonnet-4-20250514", "input_tokens": 5000, "output_tokens": 2000, "calls": 5},
        ]
        report = estimator.estimate(telemetry, queries_per_day=100)
        assert isinstance(report, CostReport)
        assert report.daily_cost > 0
        assert report.monthly_cost > 0
        assert report.monthly_cost == pytest.approx(report.daily_cost * 30, rel=1e-9)

    def test_zero_queries_returns_zero(self) -> None:
        estimator = CostEstimator()
        report = estimator.estimate([], queries_per_day=0)
        assert report.daily_cost == 0.0
        assert report.monthly_cost == 0.0

    def test_report_includes_breakdown(self) -> None:
        estimator = CostEstimator()
        telemetry = [
            {"model": "text-embedding-3-large", "input_tokens": 500, "output_tokens": 0, "calls": 1},
        ]
        report = estimator.estimate(telemetry, queries_per_day=50)
        assert len(report.breakdown) == 1
        assert report.breakdown[0]["model"] == "text-embedding-3-large"

    def test_estimate_scales_by_queries_per_day(self) -> None:
        estimator = CostEstimator()
        telemetry = [
            {"model": "text-embedding-3-large", "input_tokens": 1000, "output_tokens": 0, "calls": 10},
        ]
        report_low = estimator.estimate(telemetry, queries_per_day=10)
        report_high = estimator.estimate(telemetry, queries_per_day=100)
        assert report_high.monthly_cost > report_low.monthly_cost
