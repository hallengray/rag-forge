"""Evaluator engine factory."""

from rag_forge_evaluator.engine import EvaluatorInterface
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.progress import ProgressReporter


def create_evaluator(
    engine: str,
    judge: JudgeProvider | None = None,
    thresholds: dict[str, float] | None = None,
    progress: ProgressReporter | None = None,
    refusal_aware: bool = True,
) -> EvaluatorInterface:
    if engine == "llm-judge":
        from rag_forge_evaluator.judge.mock_judge import MockJudge
        from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator
        return LLMJudgeEvaluator(
            judge=judge or MockJudge(),
            thresholds=thresholds,
            progress=progress,
            refusal_aware=refusal_aware,
        )
    if engine == "ragas":
        from rag_forge_evaluator.engines.ragas_evaluator import RagasEvaluator
        if judge is None:
            # Default the ragas path to MockJudge when no explicit judge is
            # supplied. This matches the llm-judge branch above and prevents
            # a late, opaque "judge is None" failure from inside evaluate().
            from rag_forge_evaluator.judge.mock_judge import MockJudge
            judge = MockJudge()
        return RagasEvaluator(judge=judge, thresholds=thresholds, refusal_aware=refusal_aware)
    if engine == "deepeval":
        from rag_forge_evaluator.engines.deepeval_evaluator import DeepEvalEvaluator
        return DeepEvalEvaluator(thresholds=thresholds)
    raise ValueError(f"Unknown evaluator engine: {engine!r}. Expected one of: 'llm-judge', 'ragas', 'deepeval'.")
