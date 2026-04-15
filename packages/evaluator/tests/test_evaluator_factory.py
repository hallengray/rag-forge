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

    def test_ragas_not_installed_raises_on_evaluate(self) -> None:
        # The ragas import is deferred to evaluate() so the wrapper module
        # (and its _extract_ragas_score helper) can be imported and unit-
        # tested without the optional dep installed. v0.2.0: a judge is now
        # required — pass MockJudge() so we reach the deferred ragas import.
        #
        # This test only makes sense when ragas is NOT installed. On CI
        # matrices that include the ``[ragas]`` extra, skip it — the
        # import succeeds and the evaluator proceeds past the point where
        # the ImportError would be raised. The test_ragas_integration
        # suite covers the ragas-installed path.
        try:
            import ragas  # noqa: F401
        except ImportError:
            pass
        else:
            pytest.skip("ragas is installed — this test only asserts behaviour on systems without the [ragas] extra")

        from rag_forge_evaluator.engine import EvaluationSample

        evaluator = create_evaluator("ragas", judge=MockJudge())
        with pytest.raises(ImportError):
            evaluator.evaluate([EvaluationSample(query="q", contexts=["c"], response="r")])

    def test_deepeval_not_installed_raises(self) -> None:
        with pytest.raises(ImportError):
            create_evaluator("deepeval")

    def test_llm_judge_with_thresholds(self) -> None:
        evaluator = create_evaluator("llm-judge", judge=MockJudge(), thresholds={"faithfulness": 0.90})
        assert isinstance(evaluator, LLMJudgeEvaluator)
