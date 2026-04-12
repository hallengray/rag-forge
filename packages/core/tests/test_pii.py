"""Tests for PII scanning."""

from rag_forge_core.security.pii import (
    PIIDetection,
    PIIScannerProtocol,
    PIIScanResult,
    RegexPIIScanner,
)


class TestRegexPIIScanner:
    def test_implements_protocol(self) -> None:
        assert isinstance(RegexPIIScanner(), PIIScannerProtocol)

    def test_detects_email(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("Contact me at john@example.com please")
        assert result.has_pii
        assert any(d.entity_type == "EMAIL" for d in result.detections)

    def test_detects_phone_number(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("Call me at (555) 123-4567")
        assert result.has_pii
        assert any(d.entity_type == "PHONE_NUMBER" for d in result.detections)

    def test_detects_phone_dashes(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("My number is 555-123-4567")
        assert result.has_pii
        assert any(d.entity_type == "PHONE_NUMBER" for d in result.detections)

    def test_detects_ssn(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("My SSN is 123-45-6789")
        assert result.has_pii
        assert any(d.entity_type == "SSN" for d in result.detections)

    def test_detects_credit_card(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("Card number 4111-1111-1111-1111")
        assert result.has_pii
        assert any(d.entity_type == "CREDIT_CARD" for d in result.detections)

    def test_detects_ip_address(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("Server at 192.168.1.100")
        assert result.has_pii
        assert any(d.entity_type == "IP_ADDRESS" for d in result.detections)

    def test_clean_text_no_pii(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("What is the capital of France?")
        assert not result.has_pii
        assert result.detections == []

    def test_multiple_pii_detected(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("Email john@example.com or call 555-123-4567")
        assert result.has_pii
        assert len(result.detections) >= 2

    def test_detection_fields(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("Email is john@example.com")
        detection = next(d for d in result.detections if d.entity_type == "EMAIL")
        assert isinstance(detection, PIIDetection)
        assert detection.text == "john@example.com"
        assert isinstance(detection.start, int)
        assert isinstance(detection.end, int)
        assert 0.0 <= detection.score <= 1.0

    def test_scan_result_type(self) -> None:
        scanner = RegexPIIScanner()
        result = scanner.scan("hello")
        assert isinstance(result, PIIScanResult)
