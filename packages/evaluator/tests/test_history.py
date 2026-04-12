"""Tests for audit history tracking."""

import json
import tempfile
from pathlib import Path

from rag_forge_evaluator.history import AuditHistory, AuditHistoryEntry


def _sample_entry(score: float = 0.87) -> AuditHistoryEntry:
    return AuditHistoryEntry(
        timestamp="2026-04-12T10:00:00Z",
        metrics={"faithfulness": score, "context_relevance": 0.82},
        rmm_level=3,
        overall_score=score,
        passed=True,
    )


class TestAuditHistory:
    def test_load_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            history = AuditHistory(Path(tmpdir) / "audit-history.json")
            assert history.load() == []

    def test_append_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry())
            assert path.exists()

    def test_append_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.85))
            history.append(_sample_entry(0.90))
            entries = history.load()
            assert len(entries) == 2
            assert entries[0].overall_score == 0.85

    def test_get_previous_returns_last(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.80))
            history.append(_sample_entry(0.90))
            prev = history.get_previous()
            assert prev is not None
            assert prev.overall_score == 0.90

    def test_get_previous_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            history = AuditHistory(Path(tmpdir) / "audit-history.json")
            assert history.get_previous() is None

    def test_compute_trends_improving(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.80))
            prev = history.get_previous()
            trends = history.compute_trends({"faithfulness": 0.90, "context_relevance": 0.82}, prev)
            assert trends["faithfulness"] == "↑"

    def test_compute_trends_declining(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.90))
            prev = history.get_previous()
            trends = history.compute_trends({"faithfulness": 0.80, "context_relevance": 0.82}, prev)
            assert trends["faithfulness"] == "↓"

    def test_compute_trends_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.87))
            prev = history.get_previous()
            trends = history.compute_trends({"faithfulness": 0.88, "context_relevance": 0.82}, prev)
            assert trends["faithfulness"] == "→"

    def test_compute_trends_no_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            history = AuditHistory(Path(tmpdir) / "audit-history.json")
            trends = history.compute_trends({"faithfulness": 0.90}, None)
            assert trends == {}
