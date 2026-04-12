"""Tests for OutputGuard interceptor chain."""

from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.security.citations import CitationValidator
from rag_forge_core.security.faithfulness import FaithfulnessChecker
from rag_forge_core.security.output_guard import OutputGuard, OutputGuardResult
from rag_forge_core.security.pii import RegexPIIScanner
from rag_forge_core.security.staleness import StalenessChecker


class TestOutputGuard:
    def test_no_checks_passes(self) -> None:
        guard = OutputGuard()
        result = guard.check("Hello world", ["context"])
        assert result.passed

    def test_clean_response_passes_all_checks(self) -> None:
        guard = OutputGuard(
            faithfulness_checker=FaithfulnessChecker(
                generator=MockGenerator(fixed_response='{"score": 0.95, "reason": "grounded"}')
            ),
            pii_scanner=RegexPIIScanner(),
            citation_validator=CitationValidator(),
            staleness_checker=StalenessChecker(),
        )
        result = guard.check("Python is a language", ["Python is a programming language"])
        assert result.passed

    def test_faithfulness_failure(self) -> None:
        guard = OutputGuard(
            faithfulness_checker=FaithfulnessChecker(
                generator=MockGenerator(fixed_response='{"score": 0.2, "reason": "not grounded"}'),
                threshold=0.85,
            ),
        )
        result = guard.check("Moon is cheese", ["Python is a language"])
        assert not result.passed
        assert result.faithfulness_score == 0.2
        assert result.reason is not None

    def test_pii_in_output_blocked(self) -> None:
        guard = OutputGuard(pii_scanner=RegexPIIScanner())
        result = guard.check("The user's email is john@example.com", ["some context"])
        assert not result.passed
        assert result.pii_detected

    def test_invalid_citation_blocked(self) -> None:
        guard = OutputGuard(citation_validator=CitationValidator())
        result = guard.check(
            "According to [Source 10], this is true.",
            ["context"],
            chunk_ids=["id1"],
        )
        assert not result.passed
        assert not result.citations_valid

    def test_stale_context_blocked(self) -> None:
        import time
        guard = OutputGuard(staleness_checker=StalenessChecker(threshold_days=30))
        old_timestamp = time.time() - (60 * 86400)
        result = guard.check(
            "response",
            ["old context 1", "old context 2"],
            contexts_metadata=[
                {"source_document": "old1.md", "indexed_at": old_timestamp},
                {"source_document": "old2.md", "indexed_at": old_timestamp},
            ],
        )
        assert not result.passed
        assert result.stale_context

    def test_result_type(self) -> None:
        guard = OutputGuard()
        result = guard.check("hello", ["context"])
        assert isinstance(result, OutputGuardResult)
