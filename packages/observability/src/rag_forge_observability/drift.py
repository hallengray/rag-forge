"""Query drift detection and alerting."""

from dataclasses import dataclass


@dataclass
class DriftReport:
    """Result of a drift analysis."""

    baseline_distance: float
    is_drifting: bool
    threshold: float
    details: str | None = None


class DriftDetector:
    """Detects query distribution drift from a baseline.

    Monitors embedding distribution shift over time.
    Alerts when cosine distance exceeds threshold (default: 0.15).
    """

    def __init__(self, threshold: float = 0.15) -> None:
        self.threshold = threshold

    def analyze(self, current_embeddings: list[list[float]]) -> DriftReport:
        """Compare current query embeddings against the baseline."""
        # Stub: full implementation in Phase 4
        _ = current_embeddings
        return DriftReport(
            baseline_distance=0.0,
            is_drifting=False,
            threshold=self.threshold,
        )
