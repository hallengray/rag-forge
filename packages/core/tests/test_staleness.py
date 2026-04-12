"""Tests for staleness checking."""

import time

from rag_forge_core.security.staleness import StalenessChecker, StalenessResult


def _days_ago(days: int) -> float:
    return time.time() - (days * 86400)


class TestStalenessChecker:
    def test_fresh_context_passes(self) -> None:
        checker = StalenessChecker(threshold_days=90)
        metadata = [
            {"source_document": "doc1.md", "indexed_at": _days_ago(10)},
            {"source_document": "doc2.md", "indexed_at": _days_ago(5)},
        ]
        result = checker.check(metadata)
        assert result.passed
        assert result.stale_sources == []

    def test_stale_context_warns(self) -> None:
        checker = StalenessChecker(threshold_days=30)
        metadata = [
            {"source_document": "old.md", "indexed_at": _days_ago(60)},
            {"source_document": "new.md", "indexed_at": _days_ago(5)},
        ]
        result = checker.check(metadata)
        assert result.passed
        assert "old.md" in result.stale_sources

    def test_majority_stale_fails(self) -> None:
        checker = StalenessChecker(threshold_days=30)
        metadata = [
            {"source_document": "old1.md", "indexed_at": _days_ago(60)},
            {"source_document": "old2.md", "indexed_at": _days_ago(90)},
            {"source_document": "new.md", "indexed_at": _days_ago(5)},
        ]
        result = checker.check(metadata)
        assert not result.passed
        assert len(result.stale_sources) == 2

    def test_missing_timestamp_treated_as_fresh(self) -> None:
        checker = StalenessChecker(threshold_days=30)
        metadata = [{"source_document": "doc.md"}]
        result = checker.check(metadata)
        assert result.passed

    def test_empty_metadata_passes(self) -> None:
        checker = StalenessChecker(threshold_days=30)
        result = checker.check([])
        assert result.passed

    def test_result_type(self) -> None:
        checker = StalenessChecker()
        result = checker.check([])
        assert isinstance(result, StalenessResult)
        assert isinstance(result.threshold_days, int)

    def test_last_modified_field(self) -> None:
        checker = StalenessChecker(threshold_days=30)
        metadata = [{"source_document": "doc.md", "last_modified": _days_ago(60)}]
        result = checker.check(metadata)
        assert result.passed
        assert "doc.md" in result.stale_sources
