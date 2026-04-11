"""Base protocol for individual evaluation metrics."""
from typing import Protocol, runtime_checkable

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider


@runtime_checkable
class MetricEvaluator(Protocol):
    def name(self) -> str: ...

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult: ...

    def default_threshold(self) -> float: ...
