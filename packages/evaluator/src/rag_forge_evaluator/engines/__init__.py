"""Evaluator engine factory."""

from rag_forge_evaluator.engine import EvaluatorInterface
from rag_forge_evaluator.judge.base import JudgeProvider


def create_evaluator(
    engine: str,
    judge: JudgeProvider | None = None,
    thresholds: dict[str, float] | None = None,
) -> EvaluatorInterface:
    if engine == "llm-judge":
        from rag_forge_evaluator.judge.mock_judge import MockJudge
        from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator
        return LLMJudgeEvaluator(judge=judge or MockJudge(), thresholds=thresholds)
    if engine == "ragas":
        from rag_forge_evaluator.engines.ragas_evaluator import RagasEvaluator
        return RagasEvaluator(thresholds=thresholds)
    if engine == "deepeval":
        from rag_forge_evaluator.engines.deepeval_evaluator import DeepEvalEvaluator
        return DeepEvalEvaluator(thresholds=thresholds)
    raise ValueError(f"Unknown evaluator engine: {engine!r}. Expected one of: 'llm-judge', 'ragas', 'deepeval'.")
