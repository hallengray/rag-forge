"""Tests for citation validation."""

from rag_forge_core.security.citations import CitationValidationResult, CitationValidator


class TestCitationValidator:
    def test_valid_citations_pass(self) -> None:
        validator = CitationValidator()
        result = validator.check("According to [Source 1], Python is great. [Source 2] confirms this.", valid_source_count=3)
        assert result.passed
        assert result.valid_citations == 2
        assert result.invalid_citations == []

    def test_invalid_citation_fails(self) -> None:
        validator = CitationValidator()
        result = validator.check("According to [Source 5], this is true.", valid_source_count=3)
        assert not result.passed
        assert "[Source 5]" in result.invalid_citations

    def test_no_citations_passes(self) -> None:
        validator = CitationValidator()
        result = validator.check("Python is a programming language.", valid_source_count=3)
        assert result.passed
        assert result.total_citations == 0

    def test_mixed_valid_invalid(self) -> None:
        validator = CitationValidator()
        result = validator.check("[Source 1] says yes, but [Source 10] disagrees.", valid_source_count=3)
        assert not result.passed
        assert result.valid_citations == 1
        assert "[Source 10]" in result.invalid_citations

    def test_result_type(self) -> None:
        validator = CitationValidator()
        result = validator.check("Hello", valid_source_count=1)
        assert isinstance(result, CitationValidationResult)

    def test_custom_pattern(self) -> None:
        validator = CitationValidator(citation_pattern=r"\[Ref \d+\]")
        result = validator.check("[Ref 1] says hello", valid_source_count=2)
        assert result.passed
        assert result.total_citations == 1
