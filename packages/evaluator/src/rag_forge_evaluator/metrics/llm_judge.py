"""LLM-as-Judge evaluator that delegates to individual metric evaluators."""

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
    SampleResult,
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


def _determine_root_cause(
    sample_metrics: dict[str, float], thresholds: dict[str, float]
) -> str:
    """Determine whether a poor result is due to retrieval, generation, or both."""
    retrieval_fail = sample_metrics.get("context_relevance", 1.0) < thresholds.get(
        "context_relevance", 0.80
    )
    generation_fail = sample_metrics.get("faithfulness", 1.0) < thresholds.get(
        "faithfulness", 0.85
    )
    if retrieval_fail and generation_fail:
        return "both"
    if retrieval_fail:
        return "retrieval"
    if generation_fail:
        return "generation"
    return "none"


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
        sample_results: list[SampleResult] = []

        for sample in samples:
            sample_metric_scores: dict[str, float] = {}
            for metric in self._metrics:
                result = metric.evaluate_sample(sample, self._judge)
                metric_scores[metric.name()].append(result.score)
                sample_metric_scores[metric.name()] = result.score

            worst_metric = min(sample_metric_scores, key=sample_metric_scores.get)  # type: ignore[arg-type]
            thresholds_map = {
                m.name(): self._thresholds.get(m.name(), m.default_threshold())
                for m in self._metrics
            }
            root_cause = _determine_root_cause(sample_metric_scores, thresholds_map)

            sample_results.append(
                SampleResult(
                    query=sample.query,
                    response=sample.response,
                    metrics=sample_metric_scores,
                    worst_metric=worst_metric,
                    root_cause=root_cause,
                )
            )

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
            sample_results=sample_results,
        )

    def supported_metrics(self) -> list[str]:
        return [m.name() for m in self._metrics]
