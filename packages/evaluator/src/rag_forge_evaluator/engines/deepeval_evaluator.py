"""DeepEval framework evaluator wrapper. Requires: pip install rag-forge-evaluator[deepeval]"""

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
)

try:
    import deepeval  # noqa: F401
except ImportError as e:
    raise ImportError("DeepEval is not installed. Install with: pip install rag-forge-evaluator[deepeval]") from e


class DeepEvalEvaluator(EvaluatorInterface):
    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self._thresholds = thresholds or {}

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        from deepeval import evaluate as deepeval_evaluate
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            ContextualRelevancyMetric,
            FaithfulnessMetric,
            HallucinationMetric,
        )
        from deepeval.test_case import LLMTestCase

        test_cases = [
            LLMTestCase(input=s.query, actual_output=s.response, retrieval_context=s.contexts, expected_output=s.expected_answer or "")
            for s in samples
        ]
        metrics = [
            FaithfulnessMetric(threshold=self._thresholds.get("faithfulness", 0.85)),
            ContextualRelevancyMetric(threshold=self._thresholds.get("contextual_relevancy", 0.80)),
            AnswerRelevancyMetric(threshold=self._thresholds.get("answer_relevancy", 0.80)),
            HallucinationMetric(threshold=self._thresholds.get("hallucination", 0.95)),
        ]
        deepeval_evaluate(test_cases, metrics)

        metric_names = ["faithfulness", "contextual_relevancy", "answer_relevancy", "hallucination"]
        aggregated: list[MetricResult] = []
        for i, name in enumerate(metric_names):
            score = float(metrics[i].score) if hasattr(metrics[i], "score") else 0.0
            threshold = float(metrics[i].threshold)
            aggregated.append(MetricResult(name=name, score=round(score, 4), threshold=threshold, passed=score >= threshold))

        overall = sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        return EvaluationResult(metrics=aggregated, overall_score=round(overall, 4), samples_evaluated=len(samples), passed=all(m.passed for m in aggregated))

    def supported_metrics(self) -> list[str]:
        return ["faithfulness", "contextual_relevancy", "answer_relevancy", "hallucination"]
