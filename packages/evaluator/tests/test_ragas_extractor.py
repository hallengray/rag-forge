"""Defensive ragas result access (Bug #6 fix).

The 2026-04-13 PearMedica audit hit
``'EvaluationResult' object has no attribute 'get'`` on ragas >=0.4
because the result type changed shape between major versions. This
test covers the defensive helper so future ragas upgrades can't
silently break the engine.
"""
from dataclasses import dataclass

from rag_forge_evaluator.engines.ragas_evaluator import _extract_ragas_score


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


def test_missing_metric_returns_zero() -> None:
    assert _extract_ragas_score({}, "faithfulness") == 0.0


def test_non_numeric_value_returns_zero() -> None:
    assert _extract_ragas_score({"faithfulness": "not a number"}, "faithfulness") == 0.0


def test_dict_with_nan_falls_through() -> None:
    """nan is a float so we accept it - the metric layer is responsible for filtering."""
    import math
    result = _extract_ragas_score({"faithfulness": float("nan")}, "faithfulness")
    assert math.isnan(result)
