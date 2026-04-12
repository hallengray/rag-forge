"""RAGAS framework evaluator wrapper. Requires: pip install rag-forge-evaluator[ragas]"""

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
)

try:
    import ragas  # noqa: F401
except ImportError as e:
    raise ImportError("RAGAS is not installed. Install with: pip install rag-forge-evaluator[ragas]") from e


class RagasEvaluator(EvaluatorInterface):
    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self._thresholds = thresholds or {}

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        if not samples:
            return EvaluationResult(metrics=[], overall_score=0.0, samples_evaluated=0, passed=False)

        from datasets import Dataset
        from ragas import evaluate as ragas_evaluate
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
            score = float(result.get(name, 0.0))
            threshold = self._thresholds.get(name, default_thresholds.get(name, 0.80))
            aggregated.append(MetricResult(name=name, score=round(score, 4), threshold=threshold, passed=score >= threshold))

        overall = sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        return EvaluationResult(metrics=aggregated, overall_score=round(overall, 4), samples_evaluated=len(samples), passed=all(m.passed for m in aggregated))

    def supported_metrics(self) -> list[str]:
        return ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
