"""Abstract base for evaluation engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EvaluationSample:
    """A single sample to evaluate."""

    query: str
    contexts: list[str]
    response: str
    expected_answer: str | None = None
    chunk_ids: list[str] | None = None


@dataclass
class MetricResult:
    """Result of a single metric evaluation."""

    name: str
    score: float
    threshold: float
    passed: bool
    details: str | None = None


@dataclass
class EvaluationResult:
    """Complete evaluation result across all metrics."""

    metrics: list[MetricResult]
    overall_score: float
    samples_evaluated: int
    passed: bool


class EvaluatorInterface(ABC):
    """Abstract interface that all evaluation engines must implement."""

    @abstractmethod
    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        """Evaluate a list of samples and return aggregated results."""

    @abstractmethod
    def supported_metrics(self) -> list[str]:
        """Return the list of metric names this evaluator supports."""
