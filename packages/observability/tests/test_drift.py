"""Tests for query drift detection."""

import math
from pathlib import Path

import pytest

from rag_forge_observability.drift import DriftBaseline, DriftDetector, DriftReport


class TestDriftBaseline:
    def test_compute_centroid(self) -> None:
        baseline = DriftBaseline(embeddings=[[1.0, 0.0], [0.0, 1.0]])
        centroid = baseline.centroid
        assert len(centroid) == 2
        assert math.isclose(centroid[0], 0.5, abs_tol=1e-9)
        assert math.isclose(centroid[1], 0.5, abs_tol=1e-9)

    def test_save_and_load(self, tmp_path: Path) -> None:
        baseline = DriftBaseline(embeddings=[[1.0, 2.0], [3.0, 4.0]])
        path = tmp_path / "baseline.json"
        baseline.save(path)
        loaded = DriftBaseline.load(path)
        assert loaded.embeddings == baseline.embeddings

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            DriftBaseline.load(tmp_path / "missing.json")

    def test_empty_embeddings_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one embedding"):
            DriftBaseline(embeddings=[])


class TestDriftDetector:
    def test_no_drift_when_identical(self) -> None:
        baseline = DriftBaseline(embeddings=[[1.0, 0.0, 0.0]])
        detector = DriftDetector(threshold=0.15)
        report = detector.analyze(
            current_embeddings=[[1.0, 0.0, 0.0]],
            baseline=baseline,
        )
        assert not report.is_drifting
        assert report.baseline_distance < 0.15

    def test_drift_detected_when_orthogonal(self) -> None:
        baseline = DriftBaseline(embeddings=[[1.0, 0.0, 0.0]])
        detector = DriftDetector(threshold=0.15)
        report = detector.analyze(
            current_embeddings=[[0.0, 1.0, 0.0]],
            baseline=baseline,
        )
        assert report.is_drifting
        assert report.baseline_distance > 0.15

    def test_custom_threshold(self) -> None:
        baseline = DriftBaseline(embeddings=[[1.0, 0.0]])
        detector = DriftDetector(threshold=0.99)
        report = detector.analyze(
            current_embeddings=[[0.9, 0.1]],
            baseline=baseline,
        )
        assert isinstance(report.is_drifting, bool)

    def test_report_includes_details(self) -> None:
        baseline = DriftBaseline(embeddings=[[1.0, 0.0]])
        detector = DriftDetector(threshold=0.15)
        report = detector.analyze(
            current_embeddings=[[0.0, 1.0]],
            baseline=baseline,
        )
        assert report.threshold == 0.15
        assert report.details is not None


class TestDriftDetectorSaveBaseline:
    def test_save_baseline_from_embeddings(self, tmp_path: Path) -> None:
        detector = DriftDetector(threshold=0.15)
        path = tmp_path / "baseline.json"
        detector.save_baseline([[1.0, 2.0], [3.0, 4.0]], path)
        loaded = DriftBaseline.load(path)
        assert len(loaded.embeddings) == 2
