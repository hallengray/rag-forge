"""Tests for the drift CLI entry point."""

import json
from pathlib import Path

from rag_forge_observability.cli import cmd_drift_report, cmd_drift_save_baseline


class TestDriftCLI:
    def test_save_baseline_creates_file(self, tmp_path: Path) -> None:
        embeddings_file = tmp_path / "embeddings.json"
        embeddings_file.write_text(json.dumps({"embeddings": [[1.0, 0.0], [0.0, 1.0]]}))
        baseline_path = tmp_path / "baseline.json"

        result = cmd_drift_save_baseline(
            embeddings_path=str(embeddings_file),
            baseline_path=str(baseline_path),
        )
        assert result["success"] is True
        assert baseline_path.exists()

    def test_report_no_drift(self, tmp_path: Path) -> None:
        baseline_path = tmp_path / "baseline.json"
        baseline_data = {"embeddings": [[1.0, 0.0], [0.9, 0.1]]}
        baseline_path.write_text(json.dumps(baseline_data))

        current_path = tmp_path / "current.json"
        current_data = {"embeddings": [[1.0, 0.0], [0.95, 0.05]]}
        current_path.write_text(json.dumps(current_data))

        result = cmd_drift_report(
            current_path=str(current_path),
            baseline_path=str(baseline_path),
            threshold=0.15,
        )
        assert result["success"] is True
        assert result["is_drifting"] is False

    def test_report_with_drift(self, tmp_path: Path) -> None:
        baseline_path = tmp_path / "baseline.json"
        baseline_data = {"embeddings": [[1.0, 0.0]]}
        baseline_path.write_text(json.dumps(baseline_data))

        current_path = tmp_path / "current.json"
        current_data = {"embeddings": [[0.0, 1.0]]}
        current_path.write_text(json.dumps(current_data))

        result = cmd_drift_report(
            current_path=str(current_path),
            baseline_path=str(baseline_path),
            threshold=0.15,
        )
        assert result["success"] is True
        assert result["is_drifting"] is True

    def test_report_missing_baseline_returns_error(self, tmp_path: Path) -> None:
        current_path = tmp_path / "current.json"
        current_path.write_text(json.dumps({"embeddings": [[1.0, 0.0]]}))

        result = cmd_drift_report(
            current_path=str(current_path),
            baseline_path=str(tmp_path / "missing.json"),
            threshold=0.15,
        )
        assert result["success"] is False
        assert "error" in result
