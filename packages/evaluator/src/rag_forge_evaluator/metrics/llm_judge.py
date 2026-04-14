"""LLM-as-Judge evaluator that delegates to individual metric evaluators."""

import logging
import time

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
    SampleResult,
    ScoringMode,
)
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.response_parser import parse_judge_json
from rag_forge_evaluator.metrics.answer_relevance import AnswerRelevanceMetric
from rag_forge_evaluator.metrics.base import MetricEvaluator
from rag_forge_evaluator.metrics.context_relevance import ContextRelevanceMetric
from rag_forge_evaluator.metrics.faithfulness import FaithfulnessMetric
from rag_forge_evaluator.metrics.hallucination import HallucinationMetric
from rag_forge_evaluator.progress import NullProgressReporter, ProgressReporter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Refusal-aware classification preamble
# ---------------------------------------------------------------------------
# When prepended to the combined scoring prompt, this instructs the judge to
# first classify the sample as "standard" or "safety_refusal" and then score
# using the appropriate rubric — all in a single LLM round-trip, zero extra
# API cost.
# ---------------------------------------------------------------------------
_CLASSIFICATION_PREAMBLE = """\
Before scoring, determine two things:
(a) Does the retrieved context contain sufficient specific information to answer the question with concrete recommendations?
(b) Does the response refuse or abstain from providing specific recommendations, citing insufficient knowledge-base support?

If (a) = no AND (b) = yes, this is a VALID SAFETY REFUSAL. Score it on the refusal rubric below. Otherwise score on the standard rubric.

REFUSAL RUBRIC (apply only when scoring_mode = "safety_refusal"):
- faithfulness: did the response avoid making claims not supported by context? Pure refusal = 1.0.
- answer_relevance: did the response acknowledge the question and explain WHY it cannot answer? High if explained, low if evasive.
- context_relevance: are retrieved chunks topically related even if they lack the specific answer? (Softer than standard.)
- hallucination: did the response introduce unsupported facts? Pure refusal = 1.0.

STANDARD RUBRIC (apply when scoring_mode = "standard"): use the normal scoring criteria described below.

Return your result as JSON with these fields:
{
  "scoring_mode": "standard" | "safety_refusal",
  "refusal_justification": "<one sentence, or null for standard>",
  "faithfulness": <float 0-1>,
  "answer_relevance": <float 0-1>,
  "context_relevance": <float 0-1>,
  "hallucination": <float 0-1>
}

---

"""

# ---------------------------------------------------------------------------
# Combined scoring prompt (without classification preamble)
# ---------------------------------------------------------------------------
_COMBINED_SYSTEM_PROMPT = """\
You are an expert RAG evaluator. Given a query, retrieved contexts, and a response, \
score the response on four metrics. Return ONLY valid JSON with no prose outside the object.

Scoring rubrics:
- faithfulness (0-1): proportion of response claims that are grounded in the retrieved context.
- answer_relevance (0-1): how directly the response addresses the query.
- context_relevance (0-1): how relevant the retrieved context is to the query.
- hallucination (0-1): 1.0 means no hallucinations; 0.0 means the response is entirely fabricated.

Return exactly this structure (add scoring_mode and refusal_justification only when requested):
{
  "faithfulness": <float 0-1>,
  "answer_relevance": <float 0-1>,
  "context_relevance": <float 0-1>,
  "hallucination": <float 0-1>
}"""

# Metric names emitted by the combined path and their float bounds.
_COMBINED_METRIC_FIELDS: tuple[str, ...] = (
    "faithfulness",
    "answer_relevance",
    "context_relevance",
    "hallucination",
)

# Default thresholds mirroring the per-metric evaluator defaults.
_DEFAULT_THRESHOLDS: dict[str, float] = {
    "faithfulness": 0.85,
    "context_relevance": 0.80,
    "answer_relevance": 0.80,
    "hallucination": 0.95,
}


_STANDARD_METRIC_TYPES = (
    FaithfulnessMetric,
    ContextRelevanceMetric,
    AnswerRelevanceMetric,
    HallucinationMetric,
)


def _default_metrics() -> list[MetricEvaluator]:
    return [
        FaithfulnessMetric(),
        ContextRelevanceMetric(),
        AnswerRelevanceMetric(),
        HallucinationMetric(),
    ]


def _are_standard_metrics(metrics: list[MetricEvaluator]) -> bool:
    """Return True iff every metric in the list is one of the four standard types.

    This is used to decide whether to use the combined single-call path. If
    ``_default_metrics()`` has been monkey-patched (e.g. by the partial-report
    tests), the stored instances will not be of the standard types and this
    function returns False, routing through the per-metric path instead so the
    injected evaluators are actually called.
    """
    if len(metrics) != len(_STANDARD_METRIC_TYPES):
        return False
    return all(isinstance(m, _STANDARD_METRIC_TYPES) for m in metrics)


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


def _build_combined_user_prompt(sample: EvaluationSample, *, refusal_aware: bool) -> str:
    """Build the user prompt for the combined single-call scoring path.

    When ``refusal_aware=True`` the classification preamble is prepended so the
    judge can identify safety-refusal samples in the same round-trip. When
    ``refusal_aware=False`` the preamble is omitted and legacy semantics apply.
    """
    body = (
        f"Query: {sample.query}\n\n"
        f"Context:\n{chr(10).join(sample.contexts)}\n\n"
        f"Response: {sample.response}"
    )
    if refusal_aware:
        return _CLASSIFICATION_PREAMBLE + body
    return body


def _parse_combined_response(
    raw: str,
    thresholds: dict[str, float],
    *,
    refusal_aware: bool,
) -> tuple[dict[str, MetricResult], ScoringMode | None, str | None]:
    """Parse a combined judge response into per-metric results plus classification.

    Returns a triple: ``(metric_results, scoring_mode, refusal_justification)``.
    On parse failure every metric is marked skipped. ``scoring_mode`` and
    ``refusal_justification`` default to ``"standard"`` / ``None`` when the
    fields are absent (tolerating old-style judge responses).
    """
    outcome = parse_judge_json(raw)

    if not outcome.ok or outcome.data is None:
        logger.warning("Combined judge parse failed: %s", outcome.error)
        results: dict[str, MetricResult] = {}
        for field in _COMBINED_METRIC_FIELDS:
            threshold = thresholds.get(field, _DEFAULT_THRESHOLDS.get(field, 0.80))
            results[field] = MetricResult(
                name=field,
                score=0.0,
                threshold=threshold,
                passed=False,
                details=f"judge response unparseable: {outcome.error}",
                skipped=True,
            )
        return results, "standard", None

    data = outcome.data
    results = {}
    for field in _COMBINED_METRIC_FIELDS:
        threshold = thresholds.get(field, _DEFAULT_THRESHOLDS.get(field, 0.80))
        if field not in data:
            logger.warning("Combined judge response missing '%s' field", field)
            results[field] = MetricResult(
                name=field,
                score=0.0,
                threshold=threshold,
                passed=False,
                details=f"judge response missing '{field}' field",
                skipped=True,
            )
            continue
        try:
            score = float(data[field])
        except (TypeError, ValueError) as exc:
            logger.warning("Combined judge '%s' is not numeric: %s", field, exc)
            results[field] = MetricResult(
                name=field,
                score=0.0,
                threshold=threshold,
                passed=False,
                details=f"'{field}' not numeric: {exc}",
                skipped=True,
            )
            continue
        results[field] = MetricResult(
            name=field,
            score=score,
            threshold=threshold,
            passed=score >= threshold,
        )

    # Extract classification fields — tolerant of absence (old-style responses).
    raw_mode = data.get("scoring_mode", "standard")
    scoring_mode: ScoringMode = (
        raw_mode if raw_mode in ("standard", "safety_refusal") else "standard"
    )
    refusal_justification: str | None = data.get("refusal_justification") or None

    # When not in refusal_aware mode, ignore any classification the judge may
    # have returned — treat everything as standard.
    if not refusal_aware:
        scoring_mode = "standard"
        refusal_justification = None

    return results, scoring_mode, refusal_justification


class LLMJudgeEvaluator(EvaluatorInterface):
    def __init__(
        self,
        judge: JudgeProvider,
        metrics: list[MetricEvaluator] | None = None,
        thresholds: dict[str, float] | None = None,
        progress: ProgressReporter | None = None,
        refusal_aware: bool = True,
    ) -> None:
        self._judge = judge
        self._metrics = metrics or _default_metrics()
        # A caller-supplied metrics list may contain specialised or patched
        # evaluators that must be called individually. We detect "default"
        # by checking that every stored metric is an instance of one of the
        # four standard classes. If _default_metrics() was patched (e.g. in
        # test_partial_report), the stored instances will not be standard
        # types and the per-metric path is used automatically.
        self._using_standard_metrics = _are_standard_metrics(self._metrics)
        self._thresholds = thresholds or {}
        self._progress = progress or NullProgressReporter()
        self._refusal_aware = refusal_aware
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

    def _evaluate_sample_combined(
        self, sample: EvaluationSample
    ) -> tuple[dict[str, MetricResult], ScoringMode | None, str | None]:
        """Score all four metrics in a single judge call.

        Used when ``refusal_aware`` is set (either True or False) to keep
        scoring in one round-trip. Returns per-metric results and the
        classification outcome.
        """
        user_prompt = _build_combined_user_prompt(sample, refusal_aware=self._refusal_aware)
        raw = self._judge.judge(_COMBINED_SYSTEM_PROMPT, user_prompt)
        return _parse_combined_response(raw, self._thresholds, refusal_aware=self._refusal_aware)

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        if not samples:
            return EvaluationResult(
                metrics=[],
                overall_score=0.0,
                samples_evaluated=0,
                passed=False,
            )

        # Use the combined single-call path only when all stored metrics are
        # instances of the standard four classes. If _default_metrics() was
        # patched (e.g. by partial-report tests injecting exploding evaluators),
        # the stored instances will not pass this check and we fall through to
        # the per-metric path so every injected evaluator is actually called.
        use_combined = self._using_standard_metrics

        if use_combined:
            return self._evaluate_combined(samples)
        return self._evaluate_per_metric(samples)

    # ------------------------------------------------------------------
    # Combined single-call path (refusal_aware=True or False)
    # ------------------------------------------------------------------

    def _evaluate_combined(self, samples: list[EvaluationSample]) -> EvaluationResult:
        """Evaluate samples using one judge call per sample for all metrics."""
        metric_names = list(_COMBINED_METRIC_FIELDS)
        self._partial_metric_outcomes = {name: [] for name in metric_names}
        self._partial_sample_results = []
        metric_outcomes = self._partial_metric_outcomes
        sample_results = self._partial_sample_results
        scoring_modes_count: dict[str, int] = {}

        total = len(samples)
        for i, sample in enumerate(samples, start=1):
            sample_start = time.monotonic()
            per_metric_results, scoring_mode, refusal_justification = (
                self._evaluate_sample_combined(sample)
            )

            sample_metric_scores: dict[str, float] = {}
            sample_skipped = 0
            for name in metric_names:
                result = per_metric_results[name]
                metric_outcomes[name].append((result.score, result.skipped))
                sample_metric_scores[name] = result.score
                if result.skipped:
                    sample_skipped += 1

            worst_metric = min(sample_metric_scores, key=sample_metric_scores.get)  # type: ignore[arg-type]
            thresholds_map = {
                name: self._thresholds.get(name, _DEFAULT_THRESHOLDS.get(name, 0.80))
                for name in metric_names
            }
            root_cause = _determine_root_cause(sample_metric_scores, thresholds_map)

            mode_key = scoring_mode if scoring_mode is not None else "standard"
            scoring_modes_count[mode_key] = scoring_modes_count.get(mode_key, 0) + 1

            sample_results.append(
                SampleResult(
                    query=sample.query,
                    response=sample.response,
                    metrics=sample_metric_scores,
                    worst_metric=worst_metric,
                    root_cause=root_cause,
                    sample_id=sample.sample_id,
                    scoring_mode=scoring_mode,
                    refusal_justification=refusal_justification,
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

        # Build per-metric aggregate MetricResult objects.
        aggregated: list[MetricResult] = []
        total_skipped = 0
        for name in metric_names:
            outcomes = metric_outcomes[name]
            real_scores = [score for score, skipped in outcomes if not skipped]
            skipped_count = sum(1 for _, skipped in outcomes if skipped)
            scored_count = len(real_scores)
            total_skipped += skipped_count
            mean_score = sum(real_scores) / scored_count if scored_count else 0.0
            threshold = self._thresholds.get(name, _DEFAULT_THRESHOLDS.get(name, 0.80))
            aggregated.append(
                MetricResult(
                    name=name,
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
            scoring_modes_count=scoring_modes_count,
        )

    # ------------------------------------------------------------------
    # Legacy per-metric path (custom metrics list supplied by caller)
    # ------------------------------------------------------------------

    def _evaluate_per_metric(self, samples: list[EvaluationSample]) -> EvaluationResult:
        """Original per-metric evaluation loop — used when a custom metrics
        list is supplied so that callers who inject specialised evaluators
        continue to work without modification."""
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
