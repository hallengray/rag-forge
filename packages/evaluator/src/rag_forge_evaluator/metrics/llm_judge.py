"""LLM-as-Judge evaluator that delegates to individual metric evaluators."""
from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
)
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.metrics.answer_relevance import AnswerRelevanceMetric
from rag_forge_evaluator.metrics.base import MetricEvaluator
from rag_forge_evaluator.metrics.context_relevance import ContextRelevanceMetric
from rag_forge_evaluator.metrics.faithfulness import FaithfulnessMetric
from rag_forge_evaluator.metrics.hallucination import HallucinationMetric


def _default_metrics() -> list[MetricEvaluator]:
    return [
        FaithfulnessMetric(),
        ContextRelevanceMetric(),
        AnswerRelevanceMetric(),
        HallucinationMetric(),
    ]


class LLMJudgeEvaluator(EvaluatorInterface):
    def __init__(
        self,
        judge: JudgeProvider,
        metrics: list[MetricEvaluator] | None = None,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        self._judge = judge
        self._metrics = metrics or _default_metrics()
        self._thresholds = thresholds or {}

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        if not samples:
            return EvaluationResult(
                metrics=[],
                overall_score=0.0,
                samples_evaluated=0,
                passed=False,
            )

        metric_scores: dict[str, list[float]] = {m.name(): [] for m in self._metrics}
        for sample in samples:
            for metric in self._metrics:
                result = metric.evaluate_sample(sample, self._judge)
                metric_scores[metric.name()].append(result.score)

        aggregated: list[MetricResult] = []
        for metric in self._metrics:
            scores = metric_scores[metric.name()]
            mean_score = sum(scores) / len(scores) if scores else 0.0
            threshold = self._thresholds.get(metric.name(), metric.default_threshold())
            aggregated.append(
                MetricResult(
                    name=metric.name(),
                    score=round(mean_score, 4),
                    threshold=threshold,
                    passed=mean_score >= threshold,
                )
            )

        overall = (
            sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        )
        return EvaluationResult(
            metrics=aggregated,
            overall_score=round(overall, 4),
            samples_evaluated=len(samples),
            passed=all(m.passed for m in aggregated),
        )

    def supported_metrics(self) -> list[str]:
        return [m.name() for m in self._metrics]
