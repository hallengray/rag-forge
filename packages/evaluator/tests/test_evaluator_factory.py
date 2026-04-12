"""Tests for evaluator engine factory."""

import pytest

from rag_forge_evaluator.engine import EvaluatorInterface
from rag_forge_evaluator.engines import create_evaluator
from rag_forge_evaluator.judge.mock_judge import MockJudge
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator


class TestCreateEvaluator:
    def test_llm_judge_returns_correct_type(self) -> None:
        evaluator = create_evaluator("llm-judge", judge=MockJudge())
        assert isinstance(evaluator, LLMJudgeEvaluator)
        assert isinstance(evaluator, EvaluatorInterface)

    def test_unknown_engine_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown evaluator engine"):
            create_evaluator("invalid")

    def test_ragas_not_installed_raises(self) -> None:
        with pytest.raises(ImportError):
            create_evaluator("ragas")

    def test_deepeval_not_installed_raises(self) -> None:
        with pytest.raises(ImportError):
            create_evaluator("deepeval")

    def test_llm_judge_with_thresholds(self) -> None:
        evaluator = create_evaluator("llm-judge", judge=MockJudge(), thresholds={"faithfulness": 0.90})
        assert isinstance(evaluator, LLMJudgeEvaluator)
