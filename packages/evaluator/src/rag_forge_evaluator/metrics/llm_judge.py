"""LLM-as-Judge evaluator that delegates to individual metric evaluators."""

import time

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
from rag_forge_evaluator.progress import NullProgressReporter, ProgressReporter


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
    generation_fail = (
        sample_metrics.get("faithfulness", 1.0) < thresholds.get("faithfulness", 0.85)
        or sample_metrics.get("answer_relevance", 1.0)
        < thresholds.get("answer_relevance", 0.80)
        or sample_metrics.get("hallucination", 1.0)
        < thresholds.get("hallucination", 0.95)
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
        progress: ProgressReporter | None = None,
    ) -> None:
        self._judge = judge
        self._metrics = metrics or _default_metrics()
        self._thresholds = thresholds or {}
        self._progress = progress or NullProgressReporter()
        # Partial state — populated incrementally during evaluate() so that if
        # the loop crashes, the orchestrator can still recover everything that
        # was scored before the abort and write audit-report.partial.json.
        self._partial_sample_results: list[SampleResult] = []
        self._partial_metric_outcomes: dict[str, list[tuple[float, bool]]] = {}

    @property
    def partial_sample_results(self) -> list[SampleResult]:
        return self._partial_sample_results

    def compute_partial_aggregates(self) -> dict[str, dict[str, float | int]]:
        """Compute subset aggregates over whatever has been scored so far.

        Returns a dict of ``metric_name -> {score, scored_count, skipped_count}``
        using the same mean-over-non-skipped logic as the happy path. Intended
        for inclusion in ``audit-report.partial.json``'s ``partial_metrics``
        block — clearly namespaced so no caller mistakes it for a full-run
        aggregate.
        """
        out: dict[str, dict[str, float | int]] = {}
        for name, outcomes in self._partial_metric_outcomes.items():
            real = [s for s, skipped in outcomes if not skipped]
            skipped_count = sum(1 for _, skipped in outcomes if skipped)
            mean = round(sum(real) / len(real), 4) if real else 0.0
            out[name] = {
                "score": mean,
                "scored_count": len(real),
                "skipped_count": skipped_count,
            }
        return out

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        if not samples:
            return EvaluationResult(
                metrics=[],
                overall_score=0.0,
                samples_evaluated=0,
                passed=False,
            )

        # Reset and alias the partial buffers so mid-loop exceptions leave the
        # instance holding everything scored so far.
        self._partial_metric_outcomes = {m.name(): [] for m in self._metrics}
        self._partial_sample_results = []
        metric_outcomes = self._partial_metric_outcomes
        sample_results = self._partial_sample_results

        total = len(samples)
        for i, sample in enumerate(samples, start=1):
            sample_start = time.monotonic()
            sample_metric_scores: dict[str, float] = {}
            sample_skipped = 0
            for metric in self._metrics:
                result = metric.evaluate_sample(sample, self._judge)
                metric_outcomes[metric.name()].append((result.score, result.skipped))
                sample_metric_scores[metric.name()] = result.score
                if result.skipped:
                    sample_skipped += 1

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

            self._progress.sample_scored(
                index=i,
                total=total,
                query_preview=sample.query,
                metrics=sample_metric_scores,
                skipped_count=sample_skipped,
                elapsed_seconds=time.monotonic() - sample_start,
            )

        aggregated: list[MetricResult] = []
        total_skipped = 0
        for metric in self._metrics:
            outcomes = metric_outcomes[metric.name()]
            real_scores = [score for score, skipped in outcomes if not skipped]
            skipped_count = sum(1 for _, skipped in outcomes if skipped)
            scored_count = len(real_scores)
            total_skipped += skipped_count
            mean_score = sum(real_scores) / scored_count if scored_count else 0.0
            threshold = self._thresholds.get(metric.name(), metric.default_threshold())
            aggregated.append(
                MetricResult(
                    name=metric.name(),
                    score=round(mean_score, 4),
                    threshold=threshold,
                    passed=scored_count > 0 and mean_score >= threshold,
                    skipped_count=skipped_count,
                    scored_count=scored_count,
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
            skipped_evaluations=total_skipped,
        )

    def supported_metrics(self) -> list[str]:
        return [m.name() for m in self._metrics]
