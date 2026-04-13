"""RAGAS framework evaluator wrapper. Requires: pip install rag-forge-evaluator[ragas]

The ragas import is deferred into ``RagasEvaluator.evaluate`` so that the
``_extract_ragas_score`` helper (and the rest of this module) can be
imported without ragas installed - the helper is unit-testable in
isolation.
"""

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
)


def _extract_ragas_score(result: object, name: str) -> float:
    """Extract a metric score from a ragas result object defensively.

    ragas 0.2.x returns a dict-like result supporting ``.get()``.
    ragas 0.4.x returns an ``EvaluationResult`` dataclass; ``__getitem__``
    works on it but ``.get()`` does not.
    ragas 0.3.x sits between the two with intermediate forms.

    The pyproject pins ragas to ``>=0.2.10,<0.3`` for v0.1.1 (where
    ``.get()`` works), but this helper falls back through dict access,
    item access, attribute access, and finally a numeric cast so future
    upgrades degrade gracefully instead of crashing the audit after
    paid judge calls have already run.
    """
    if hasattr(result, "get"):
        try:
            value = result.get(name, None)
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            pass
    try:
        return float(result[name])  # type: ignore[index]
    except (KeyError, TypeError, ValueError, IndexError):
        pass
    if hasattr(result, name):
        try:
            return float(getattr(result, name))
        except (TypeError, ValueError):
            pass
    return 0.0


class RagasEvaluator(EvaluatorInterface):
    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self._thresholds = thresholds or {}

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        if not samples:
            return EvaluationResult(metrics=[], overall_score=0.0, samples_evaluated=0, passed=False)

        try:
            from datasets import Dataset
            from ragas import evaluate as ragas_evaluate
        except ImportError as e:
            msg = "RAGAS is not installed. Install with: pip install rag-forge-evaluator[ragas]"
            raise ImportError(msg) from e
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        data = {
            "question": [s.query for s in samples],
            "answer": [s.response for s in samples],
            "contexts": [s.contexts for s in samples],
            "ground_truth": [s.expected_answer or "" for s in samples],
        }
        dataset = Dataset.from_dict(data)
        result = ragas_evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])

        metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        default_thresholds = {"faithfulness": 0.85, "answer_relevancy": 0.80, "context_precision": 0.80, "context_recall": 0.70}
        aggregated: list[MetricResult] = []
        for name in metric_names:
            score = _extract_ragas_score(result, name)
            threshold = self._thresholds.get(name, default_thresholds.get(name, 0.80))
            aggregated.append(MetricResult(name=name, score=round(score, 4), threshold=threshold, passed=score >= threshold))

        overall = sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        return EvaluationResult(metrics=aggregated, overall_score=round(overall, 4), samples_evaluated=len(samples), passed=all(m.passed for m in aggregated))

    def supported_metrics(self) -> list[str]:
        return ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
