"""Tests for faithfulness checking."""

from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.security.faithfulness import FaithfulnessChecker, FaithfulnessResult


class TestFaithfulnessChecker:
    def test_result_type(self) -> None:
        checker = FaithfulnessChecker(generator=MockGenerator())
        result = checker.check("Some response", ["Some context"])
        assert isinstance(result, FaithfulnessResult)

    def test_returns_score(self) -> None:
        checker = FaithfulnessChecker(generator=MockGenerator())
        result = checker.check("Some response", ["Some context"])
        assert isinstance(result.score, float)
        assert isinstance(result.threshold, float)

    def test_high_score_passes(self) -> None:
        checker = FaithfulnessChecker(
            generator=MockGenerator(fixed_response='{"score": 0.95, "reason": "fully grounded"}'),
            threshold=0.85,
        )
        result = checker.check("Python is a language", ["Python is a programming language"])
        assert result.passed
        assert result.score == 0.95

    def test_low_score_fails(self) -> None:
        checker = FaithfulnessChecker(
            generator=MockGenerator(fixed_response='{"score": 0.3, "reason": "not grounded"}'),
            threshold=0.85,
        )
        result = checker.check("The moon is made of cheese", ["Python is a language"])
        assert not result.passed
        assert result.score == 0.3

    def test_malformed_response_defaults_to_pass(self) -> None:
        checker = FaithfulnessChecker(generator=MockGenerator())
        result = checker.check("response", ["context"])
        assert result.passed

    def test_custom_threshold(self) -> None:
        checker = FaithfulnessChecker(
            generator=MockGenerator(fixed_response='{"score": 0.7, "reason": "moderate"}'),
            threshold=0.5,
        )
        result = checker.check("response", ["context"])
        assert result.passed
        assert result.threshold == 0.5

    def test_empty_contexts(self) -> None:
        checker = FaithfulnessChecker(generator=MockGenerator())
        result = checker.check("response", [])
        assert result.passed
