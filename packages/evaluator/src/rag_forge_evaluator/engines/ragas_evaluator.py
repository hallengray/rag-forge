"""RAGAS framework evaluator wrapper.

Requires: pip install rag-forge-evaluator[ragas]
For Claude judge + Voyage embeddings: add [ragas-voyage] extra.

In v0.2.0 this adapter injects RagForgeRagasLLM and RagForgeRagasEmbeddings
into ragas so the framework never reaches for its version-fragile defaults.
Per-sample exceptions are tracked as SkipRecords instead of silently
coerced to 0.0 — this makes broken infrastructure visible in the report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
    SkipRecord,
)
from rag_forge_evaluator.engines.ragas_adapters import (
    EmbeddingProvider,
    RagForgeRagasEmbeddings,
    RagForgeRagasLLM,
)

if TYPE_CHECKING:
    from rag_forge_evaluator.judge.base import JudgeProvider


_METRIC_NAMES = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
_DEFAULT_THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.80,
    "context_recall": 0.70,
}


def _extract_ragas_score(result: object, name: str) -> float:
    """Extract a metric score from a ragas result object.

    Raises ValueError if the score cannot be extracted — the caller
    decides whether to record a SkipRecord or re-raise. No silent 0.0
    fallback (that was the bug surfaced by PearMedica Cycle 2).

    ragas 0.2.x returns a dict-like result supporting ``.get()``.
    ragas 0.4.x returns an ``EvaluationResult`` dataclass; ``__getitem__``
    works on it but ``.get()`` does not.
    ragas 0.3.x sits between the two with intermediate forms.
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
    raise ValueError(f"could not extract ragas score for metric {name!r}")


def _auto_select_provider(judge: JudgeProvider | None) -> EmbeddingProvider:
    """Pick embeddings provider from judge type.

    - ClaudeJudge (model contains 'claude') → voyage
    - MockJudge / model name contains 'mock' or equals 'fake-judge-v1' → mock
    - Anything else → openai
    - None → mock (defensive)
    """
    if judge is None:
        return "mock"
    model = judge.model_name().lower()
    if "claude" in model:
        return "voyage"
    if "mock" in model or model == "fake-judge-v1":
        return "mock"
    return "openai"


class RagasEvaluator(EvaluatorInterface):
    def __init__(
        self,
        judge: JudgeProvider | None = None,
        thresholds: dict[str, float] | None = None,
        max_tokens: int = 8192,
        embeddings_provider: EmbeddingProvider | None = None,
        refusal_aware: bool = True,
    ) -> None:
        self._judge = judge
        self._thresholds = thresholds or {}
        self._max_tokens = max_tokens
        self._embeddings_provider = embeddings_provider or _auto_select_provider(judge)
        self._refusal_aware = refusal_aware

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        if not samples:
            return EvaluationResult(metrics=[], overall_score=0.0, samples_evaluated=0, passed=False)

        if self._judge is None:
            msg = (
                "RagasEvaluator requires a judge to inject its LLM wrapper. "
                "The evaluator factory should thread this through automatically — "
                "if you see this, you are constructing RagasEvaluator directly without a judge."
            )
            raise ValueError(msg)

        try:
            from datasets import Dataset
            from ragas import evaluate as ragas_evaluate
            from ragas.metrics import (
                answer_relevancy,
                context_precision,
                context_recall,
                faithfulness,
            )
        except ImportError as exc:
            msg = "RAGAS is not installed. Install with: pip install rag-forge-evaluator[ragas]"
            raise ImportError(msg) from exc

        llm_wrapper = RagForgeRagasLLM(
            judge=self._judge,
            max_tokens=self._max_tokens,
            refusal_aware=self._refusal_aware,
        )
        embeddings_wrapper = RagForgeRagasEmbeddings(provider=self._embeddings_provider)

        data = {
            "question": [s.query for s in samples],
            "answer": [s.response for s in samples],
            "contexts": [s.contexts for s in samples],
            "ground_truth": [s.expected_answer or "" for s in samples],
        }
        dataset = Dataset.from_dict(data)

        skipped_samples: list[SkipRecord] = []
        try:
            result = ragas_evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                llm=llm_wrapper,
                embeddings=embeddings_wrapper,
            )
        except Exception as exc:
            for sample in samples:
                for metric_name in _METRIC_NAMES:
                    skipped_samples.append(
                        SkipRecord(
                            sample_id=sample.sample_id or sample.query[:40],
                            metric_name=metric_name,
                            reason=str(exc),
                            exception_type=type(exc).__name__,
                        )
                    )
            return EvaluationResult(
                metrics=[],
                overall_score=0.0,
                samples_evaluated=0,
                passed=False,
                skipped_samples=skipped_samples,
            )

        aggregated: list[MetricResult] = []
        for metric_name in _METRIC_NAMES:
            try:
                score = _extract_ragas_score(result, metric_name)
            except ValueError as exc:
                skipped_samples.append(
                    SkipRecord(
                        sample_id="<aggregate>",
                        metric_name=metric_name,
                        reason=str(exc),
                        exception_type=type(exc).__name__,
                    )
                )
                continue
            threshold = self._thresholds.get(metric_name, _DEFAULT_THRESHOLDS[metric_name])
            aggregated.append(
                MetricResult(
                    name=metric_name,
                    score=round(score, 4),
                    threshold=threshold,
                    passed=score >= threshold,
                    scored_count=len(samples),
                )
            )

        overall = sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        return EvaluationResult(
            metrics=aggregated,
            overall_score=round(overall, 4),
            samples_evaluated=len(samples),
            passed=bool(aggregated) and all(m.passed for m in aggregated),
            skipped_samples=skipped_samples,
        )

    def supported_metrics(self) -> list[str]:
        return list(_METRIC_NAMES)
