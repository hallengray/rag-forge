"""Tests for judge providers and evaluation metrics."""

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.mock_judge import MockJudge


class TestMockJudge:
    def test_implements_protocol(self) -> None:
        assert isinstance(MockJudge(), JudgeProvider)

    def test_returns_valid_json(self) -> None:
        result = MockJudge().judge("system", "user")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_model_name(self) -> None:
        assert MockJudge().model_name() == "mock-judge"

    def test_custom_response(self) -> None:
        judge = MockJudge(fixed_response='{"score": 0.95}')
        assert '"score": 0.95' in judge.judge("system", "user")
