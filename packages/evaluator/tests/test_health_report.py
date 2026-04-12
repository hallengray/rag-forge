"""Tests for pipeline health report generator."""

import json
from pathlib import Path

from rag_forge_evaluator.report.health import HealthReportGenerator, PipelineHealth


class TestPipelineHealth:
    def test_from_empty_state(self) -> None:
        health = PipelineHealth.collect(reports_dir=None, collection_name="test")
        assert health.chunk_count == 0
        assert health.latest_audit is None

    def test_from_audit_report(self, tmp_path: Path) -> None:
        report_path = tmp_path / "audit-report.json"
        report_data = {
            "overall_score": 0.82,
            "rmm_level": 3,
            "rmm_name": "Better Trust",
            "metrics": [
                {
                    "name": "faithfulness",
                    "score": 0.88,
                    "threshold": 0.85,
                    "passed": True,
                }
            ],
        }
        report_path.write_text(json.dumps(report_data))
        health = PipelineHealth.collect(
            reports_dir=str(tmp_path), collection_name="test"
        )
        assert health.latest_audit is not None
        assert health.latest_audit["overall_score"] == 0.82


class TestHealthReportGenerator:
    def test_generates_html_file(self, tmp_path: Path) -> None:
        health = PipelineHealth(
            chunk_count=100, latest_audit=None, drift_baseline_exists=False
        )
        gen = HealthReportGenerator(output_dir=str(tmp_path))
        path = gen.generate(health)
        assert path.exists()
        assert path.suffix == ".html"

    def test_html_contains_chunk_count(self, tmp_path: Path) -> None:
        health = PipelineHealth(
            chunk_count=42, latest_audit=None, drift_baseline_exists=False
        )
        gen = HealthReportGenerator(output_dir=str(tmp_path))
        path = gen.generate(health)
        content = path.read_text()
        assert "42" in content

    def test_html_contains_audit_data(self, tmp_path: Path) -> None:
        health = PipelineHealth(
            chunk_count=100,
            latest_audit={
                "overall_score": 0.85,
                "rmm_level": 3,
                "rmm_name": "Better Trust",
                "metrics": [],
            },
            drift_baseline_exists=True,
        )
        gen = HealthReportGenerator(output_dir=str(tmp_path))
        path = gen.generate(health)
        content = path.read_text()
        assert "Better Trust" in content

    def test_html_contains_drift_baseline_status(self, tmp_path: Path) -> None:
        health = PipelineHealth(
            chunk_count=0, latest_audit=None, drift_baseline_exists=True
        )
        gen = HealthReportGenerator(output_dir=str(tmp_path))
        path = gen.generate(health)
        content = path.read_text()
        assert "Baseline configured" in content

    def test_html_no_baseline(self, tmp_path: Path) -> None:
        health = PipelineHealth(
            chunk_count=0, latest_audit=None, drift_baseline_exists=False
        )
        gen = HealthReportGenerator(output_dir=str(tmp_path))
        path = gen.generate(health)
        content = path.read_text()
        assert "No baseline" in content
