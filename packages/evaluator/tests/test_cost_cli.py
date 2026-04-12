"""Tests for cost CLI entry point."""

import json
from pathlib import Path

from rag_forge_evaluator.cost import CostEstimator


class TestCostCLI:
    def test_estimate_from_telemetry_file(self, tmp_path: Path) -> None:
        telemetry_path = tmp_path / "telemetry.json"
        telemetry_data = {
            "usage": [
                {"model": "text-embedding-3-large", "input_tokens": 1000, "output_tokens": 0, "calls": 10},
                {"model": "claude-sonnet-4-20250514", "input_tokens": 5000, "output_tokens": 2000, "calls": 5},
            ],
            "queries_per_day": 100,
        }
        telemetry_path.write_text(json.dumps(telemetry_data))

        estimator = CostEstimator()
        with telemetry_path.open() as f:
            data = json.load(f)

        report = estimator.estimate(data["usage"], data["queries_per_day"])
        assert report.monthly_cost > 0
        assert len(report.breakdown) == 2
