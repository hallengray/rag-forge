"""Defensive ragas result access (Bug #6 fix).

The 2026-04-13 PearMedica audit hit
``'EvaluationResult' object has no attribute 'get'`` on ragas >=0.4
because the result type changed shape between major versions. This
test covers the defensive helper so future ragas upgrades can't
silently break the engine.

v0.2.0: the silent 0.0 fallback was replaced with a ValueError raise so
broken infrastructure is visible in the report instead of producing
quietly-wrong 0.0 scores. Tests that previously asserted 0.0 now assert
pytest.raises(ValueError).
"""
import math
from dataclasses import dataclass

import pytest

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.engines.ragas_evaluator import (
    RagasEvaluator,
    _extract_ragas_score,
)


def test_extract_from_dict_like() -> None:
    """ragas 0.2.x: result is a dict supporting .get()"""
    assert _extract_ragas_score({"faithfulness": 0.87}, "faithfulness") == 0.87


def test_extract_from_getitem_only() -> None:
    """ragas 0.4.x: EvaluationResult supports __getitem__ but not .get()"""
    class _Result:
        def __getitem__(self, key: str) -> float:
            return {"faithfulness": 0.42}[key]

    assert _extract_ragas_score(_Result(), "faithfulness") == 0.42


def test_extract_from_attribute() -> None:
    """Some result shapes expose scores as attributes."""
    @dataclass
    class _Result:
        faithfulness: float = 0.73

    assert _extract_ragas_score(_Result(), "faithfulness") == 0.73


def test_missing_metric_raises_value_error() -> None:
    """v0.2.0: silent 0.0 fallback is gone; missing key raises ValueError."""
    with pytest.raises(ValueError):
        _extract_ragas_score({}, "faithfulness")


def test_non_numeric_value_raises_value_error() -> None:
    """v0.2.0: non-numeric value raises ValueError instead of returning 0.0."""
    with pytest.raises(ValueError):
        _extract_ragas_score({"faithfulness": "not a number"}, "faithfulness")


def test_dict_with_nan_falls_through() -> None:
    """nan is a float so we accept it - the metric layer is responsible for filtering."""
    result = _extract_ragas_score({"faithfulness": float("nan")}, "faithfulness")
    assert math.isnan(result)


def test_extract_ragas_score_raises_on_unextractable_value() -> None:
    """The 0.0 fallback is gone; extractor now raises ValueError and the
    caller decides whether to skip or re-raise."""
    with pytest.raises(ValueError):
        _extract_ragas_score({"unrelated": 1.0}, "faithfulness")


def test_ragas_evaluator_accepts_judge_parameter() -> None:
    from rag_forge_evaluator.judge.mock_judge import MockJudge

    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={"faithfulness": 0.85},
    )
    assert evaluator.supported_metrics() == [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]


def test_ragas_evaluator_raises_when_judge_is_none() -> None:
    evaluator = RagasEvaluator(judge=None, thresholds={})
    samples = [EvaluationSample(query="q", contexts=["c"], response="r", sample_id="s1")]
    with pytest.raises(ValueError, match="requires a judge"):
        evaluator.evaluate(samples)
