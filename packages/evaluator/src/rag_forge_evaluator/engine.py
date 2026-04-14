"""Abstract base for evaluation engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

# Type alias for scoring modes
ScoringMode = Literal["standard", "safety_refusal"]


@dataclass
class SkipRecord:
    """A sample that could not be scored by an evaluator.

    Replaces the old 0.0-on-exception coercion.
    """

    sample_id: str
    metric_name: str
    reason: str
    exception_type: str


@dataclass
class EvaluationSample:
    """A single sample to evaluate."""

    query: str
    contexts: list[str]
    response: str
    expected_answer: str | None = None
    chunk_ids: list[str] | None = None
    sample_id: str | None = None


@dataclass
class MetricResult:
    """Result of a single metric evaluation.

    ``skipped`` indicates the metric could not be scored for this sample
    (e.g. the judge returned an unparseable response). Aggregation should
    exclude skipped results rather than treat them as zero. ``skipped_count``
    and ``scored_count`` are populated on *aggregate* MetricResult objects
    returned by an evaluator, not per-sample results.
    """

    name: str
    score: float
    threshold: float
    passed: bool
    details: str | None = None
    skipped: bool = False
    skipped_count: int = 0
    scored_count: int = 0
    scoring_mode: ScoringMode | None = None
    refusal_justification: str | None = None


@dataclass
class SampleResult:
    """Evaluation results for a single sample."""

    query: str
    response: str
    metrics: dict[str, float]
    worst_metric: str
    root_cause: str
    sample_id: str | None = None
    scoring_mode: ScoringMode | None = None
    refusal_justification: str | None = None


@dataclass
class EvaluationResult:
    """Complete evaluation result across all metrics."""

    metrics: list[MetricResult]
    overall_score: float
    samples_evaluated: int
    passed: bool
    sample_results: list[SampleResult] = field(default_factory=list)
    skipped_evaluations: int = 0
    skipped_samples: list[SkipRecord] = field(default_factory=list)
    scoring_modes_count: dict[str, int] = field(default_factory=dict)


class EvaluatorInterface(ABC):
    """Abstract interface that all evaluation engines must implement."""

    @abstractmethod
    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        """Evaluate a list of samples and return aggregated results."""

    @abstractmethod
    def supported_metrics(self) -> list[str]:
        """Return the list of metric names this evaluator supports."""
