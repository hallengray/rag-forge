"""Tests for PII collection scanner."""

from rag_forge_core.security.pii_scanner import PIICollectionScanner, PIIScanReport


class TestPIICollectionScanner:
    def test_clean_chunks_no_pii(self) -> None:
        chunks = [
            {"id": "1", "text": "RAG pipelines use vector databases."},
            {"id": "2", "text": "Chunking splits documents into smaller pieces."},
        ]
        scanner = PIICollectionScanner()
        report = scanner.scan_chunks(chunks)
        assert report.chunks_scanned == 2
        assert report.chunks_with_pii == 0
        assert len(report.pii_types) == 0

    def test_detects_email(self) -> None:
        chunks = [
            {"id": "1", "text": "Contact john@example.com for details."},
            {"id": "2", "text": "No PII here."},
        ]
        scanner = PIICollectionScanner()
        report = scanner.scan_chunks(chunks)
        assert report.chunks_with_pii == 1
        assert "EMAIL" in report.pii_types
        assert "1" in report.affected_chunks

    def test_detects_multiple_types(self) -> None:
        chunks = [
            {"id": "1", "text": "Call 555-123-4567 or email test@test.com"},
            {"id": "2", "text": "SSN: 123-45-6789"},
        ]
        scanner = PIICollectionScanner()
        report = scanner.scan_chunks(chunks)
        assert report.chunks_with_pii == 2
        assert "EMAIL" in report.pii_types
        assert "PHONE_NUMBER" in report.pii_types
        assert "SSN" in report.pii_types

    def test_empty_chunks_returns_zero(self) -> None:
        scanner = PIICollectionScanner()
        report = scanner.scan_chunks([])
        assert report.chunks_scanned == 0
        assert report.chunks_with_pii == 0

    def test_report_type(self) -> None:
        scanner = PIICollectionScanner()
        report = scanner.scan_chunks([{"id": "1", "text": "Hello"}])
        assert isinstance(report, PIIScanReport)
