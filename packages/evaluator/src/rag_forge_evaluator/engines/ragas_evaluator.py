"""RAGAS framework evaluator wrapper.

Requires: pip install rag-forge-evaluator[ragas]
For Claude judge + Voyage embeddings: add [ragas-voyage] extra.

In v0.2.0 this adapter injects RagForgeRagasLLM and RagForgeRagasEmbeddings
into ragas so the framework never reaches for its version-fragile defaults.
Per-sample exceptions are tracked as SkipRecords instead of silently
coerced to 0.0 — this makes broken infrastructure visible in the report.
"""

from __future__ import annotations

import contextlib
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
    """Extract an aggregate metric score from a ragas result object.

    Tries extraction strategies in order of RAGAS version likelihood:

    1. ``.scores`` list (RAGAS 0.4.x) — per-sample ``MetricResult``
       objects whose float score lives at ``.value``.
    2. ``.to_pandas()`` (RAGAS 0.4.x fallback) — DataFrame with metric
       names as columns and float values as cells.
    3. ``.get()`` (RAGAS 0.2.x) — dict-like access.
    4. ``[]`` indexing (generic).
    5. ``getattr`` (generic).

    Raises ``ValueError`` if all strategies fail — the caller decides
    whether to record a ``SkipRecord`` or re-raise.  No silent 0.0
    fallback (that was the bug surfaced by Cycle 2).
    """
    # --- Strategy 1: RAGAS 0.4.x .scores attribute ---
    # result.scores is a list[dict[str, MetricResult | float]], one dict
    # per sample. MetricResult wraps the float at .value.
    scores_attr = getattr(result, "scores", None)
    if isinstance(scores_attr, list) and scores_attr:
        values: list[float] = []
        for entry in scores_attr:
            if isinstance(entry, dict) and name in entry:
                raw = entry[name]
                val = getattr(raw, "value", None)
                if val is not None:
                    with contextlib.suppress(TypeError, ValueError):
                        values.append(float(val))
                else:
                    with contextlib.suppress(TypeError, ValueError):
                        values.append(float(raw))
        if values:
            return sum(values) / len(values)

    # --- Strategy 2: RAGAS 0.4.x .to_pandas() fallback ---
    to_pandas = getattr(result, "to_pandas", None)
    if callable(to_pandas):
        try:
            df = to_pandas()
            if name in df.columns:
                col = df[name].dropna()
                if len(col) > 0:
                    return float(col.mean())
        except Exception:
            pass

    # --- Strategy 3: RAGAS 0.2.x dict-like .get() ---
    if hasattr(result, "get"):
        try:
            value = result.get(name, None)
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            pass

    # --- Strategy 4: generic __getitem__ ---
    try:
        return float(result[name])  # type: ignore[index]
    except (KeyError, TypeError, ValueError, IndexError):
        pass

    # --- Strategy 5: generic attribute access ---
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
        embeddings_provider: EmbeddingProvider | None = None,
        refusal_aware: bool = True,
    ) -> None:
        self._judge = judge
        self._thresholds = thresholds or {}
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
            # RagForgeRagasLLM / RagForgeRagasEmbeddings deliberately do
            # NOT subclass ragas.llms.base.BaseRagasLLM (see that module's
            # docstring — keeps ragas a soft dep). ragas accepts them at
            # runtime through duck typing, but mypy only sees the
            # declared subclasses and reports arg-type errors. The
            # contract test in tests/test_ragas_adapters_contract.py is
            # the real guard against interface drift.
            result = ragas_evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                llm=llm_wrapper,  # type: ignore[arg-type, unused-ignore]
                embeddings=embeddings_wrapper,  # type: ignore[arg-type, unused-ignore]
            )
        except Exception as exc:
            # Whole-batch ragas crash: every sample x metric pair is a skip.
            # samples_evaluated still reflects what we *attempted* so the
            # report can honestly say "12 samples submitted, 0 metrics
            # scored, 48 skip records"; passed is False because nothing
            # was actually validated.
            skipped_samples.extend(
                self._fan_out_skip_records(samples, exc, _METRIC_NAMES),
            )
            return EvaluationResult(
                metrics=[],
                overall_score=0.0,
                samples_evaluated=len(samples),
                passed=False,
                skipped_samples=skipped_samples,
                skipped_evaluations=len(skipped_samples),
            )

        aggregated: list[MetricResult] = []
        for metric_name in _METRIC_NAMES:
            try:
                score = _extract_ragas_score(result, metric_name)
            except ValueError as exc:
                # Score extraction failed for this metric — typically
                # because ragas silently NaN-ed it after every per-job
                # exception. Fan out the skip across every sample so
                # the report's Skipped counter reflects the true blast
                # radius (48 for a 12-sample x 4-metric run), not just
                # 4 aggregate records. Cycle 3's "Skipped: 0 is still
                # wrong" finding was precisely this: the detail list
                # told the truth but the counter didn't.
                skipped_samples.extend(
                    self._fan_out_skip_records(samples, exc, [metric_name]),
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
        # A run with any skipped metrics is NOT passing, even if every
        # extracted metric cleared its threshold. Silent partial success
        # was the v0.1.3 pathology we set out to kill.
        all_metrics_scored = len(aggregated) == len(_METRIC_NAMES)
        passed = (
            all_metrics_scored
            and not skipped_samples
            and all(m.passed for m in aggregated)
        )
        return EvaluationResult(
            metrics=aggregated,
            overall_score=round(overall, 4),
            samples_evaluated=len(samples),
            passed=passed,
            skipped_samples=skipped_samples,
            skipped_evaluations=len(skipped_samples),
        )

    @staticmethod
    def _fan_out_skip_records(
        samples: list[EvaluationSample],
        exc: BaseException,
        metric_names: list[str],
    ) -> list[SkipRecord]:
        """Produce one SkipRecord per (sample, metric) pair for a failure.

        Used when ragas fails at a level coarser than a single metric/sample
        pair — whole-batch crash, or a single metric that NaN-ed for every
        sample. Attributing a single coarse failure back to every affected
        sample is what makes the Skipped counter in the report match the
        true blast radius.

        The error message is truncated to 400 chars so long Python tracebacks
        don't blow up HTML / PDF rendering downstream.
        """
        reason = str(exc)
        if len(reason) > 400:
            reason = reason[:397] + "..."
        exception_type = type(exc).__name__
        records: list[SkipRecord] = []
        for sample in samples:
            sample_id = sample.sample_id or sample.query[:40]
            for metric_name in metric_names:
                records.append(
                    SkipRecord(
                        sample_id=sample_id,
                        metric_name=metric_name,
                        reason=reason,
                        exception_type=exception_type,
                    )
                )
        return records

    def supported_metrics(self) -> list[str]:
        return list(_METRIC_NAMES)
