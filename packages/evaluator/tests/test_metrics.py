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


from rag_forge_evaluator.metrics.faithfulness import FaithfulnessMetric
from rag_forge_evaluator.metrics.context_relevance import ContextRelevanceMetric
from rag_forge_evaluator.metrics.answer_relevance import AnswerRelevanceMetric
from rag_forge_evaluator.metrics.hallucination import HallucinationMetric
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator
from rag_forge_evaluator.engine import EvaluationResult, MetricResult


def _sample() -> EvaluationSample:
    return EvaluationSample(
        query="What is Python?",
        contexts=["Python is a programming language created by Guido van Rossum."],
        response="Python is a popular programming language.",
    )


class TestFaithfulnessMetric:
    def test_name(self) -> None:
        assert FaithfulnessMetric().name() == "faithfulness"

    def test_default_threshold(self) -> None:
        assert FaithfulnessMetric().default_threshold() == 0.85

    def test_evaluate_sample(self) -> None:
        result = FaithfulnessMetric().evaluate_sample(_sample(), MockJudge())
        assert isinstance(result, MetricResult)
        assert result.name == "faithfulness"
        assert 0.0 <= result.score <= 1.0

    def test_handles_invalid_json(self) -> None:
        result = FaithfulnessMetric().evaluate_sample(_sample(), MockJudge(fixed_response="not json"))
        assert result.score == 0.0
        assert not result.passed


class TestContextRelevanceMetric:
    def test_name(self) -> None:
        assert ContextRelevanceMetric().name() == "context_relevance"

    def test_default_threshold(self) -> None:
        assert ContextRelevanceMetric().default_threshold() == 0.80

    def test_evaluate_sample(self) -> None:
        result = ContextRelevanceMetric().evaluate_sample(_sample(), MockJudge())
        assert isinstance(result, MetricResult)
        assert 0.0 <= result.score <= 1.0


class TestAnswerRelevanceMetric:
    def test_name(self) -> None:
        assert AnswerRelevanceMetric().name() == "answer_relevance"

    def test_default_threshold(self) -> None:
        assert AnswerRelevanceMetric().default_threshold() == 0.80

    def test_evaluate_sample(self) -> None:
        result = AnswerRelevanceMetric().evaluate_sample(_sample(), MockJudge())
        assert isinstance(result, MetricResult)
        assert 0.0 <= result.score <= 1.0


class TestHallucinationMetric:
    def test_name(self) -> None:
        assert HallucinationMetric().name() == "hallucination"

    def test_default_threshold(self) -> None:
        assert HallucinationMetric().default_threshold() == 0.95

    def test_evaluate_sample(self) -> None:
        result = HallucinationMetric().evaluate_sample(_sample(), MockJudge())
        assert isinstance(result, MetricResult)
        assert 0.0 <= result.score <= 1.0

    def test_handles_invalid_json(self) -> None:
        result = HallucinationMetric().evaluate_sample(_sample(), MockJudge(fixed_response="garbage"))
        assert result.score == 0.0
        assert not result.passed


class TestLLMJudgeEvaluator:
    def test_evaluate_returns_result(self) -> None:
        result = LLMJudgeEvaluator(MockJudge()).evaluate([_sample()])
        assert isinstance(result, EvaluationResult)
        assert result.samples_evaluated == 1
        assert len(result.metrics) == 4

    def test_supported_metrics(self) -> None:
        names = LLMJudgeEvaluator(MockJudge()).supported_metrics()
        assert "faithfulness" in names
        assert "context_relevance" in names
        assert "answer_relevance" in names
        assert "hallucination" in names

    def test_overall_score_is_mean(self) -> None:
        result = LLMJudgeEvaluator(MockJudge()).evaluate([_sample()])
        scores = [m.score for m in result.metrics]
        expected = sum(scores) / len(scores)
        assert abs(result.overall_score - expected) < 0.01

    def test_custom_thresholds(self) -> None:
        result = LLMJudgeEvaluator(MockJudge(), thresholds={"faithfulness": 0.99}).evaluate([_sample()])
        faith = next(m for m in result.metrics if m.name == "faithfulness")
        assert faith.threshold == 0.99

    def test_empty_samples(self) -> None:
        result = LLMJudgeEvaluator(MockJudge()).evaluate([])
        assert result.samples_evaluated == 0
        assert result.overall_score == 0.0
