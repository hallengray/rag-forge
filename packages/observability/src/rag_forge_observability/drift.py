"""Query drift detection and alerting.

Compares current query embedding distribution against a saved baseline
using centroid cosine distance. Alerts when distance exceeds threshold.
PRD spec: cosine distance > 0.15 from baseline triggers drift alert.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DriftReport:
    """Result of a drift analysis."""

    baseline_distance: float
    is_drifting: bool
    threshold: float
    details: str | None = None


class DriftBaseline:
    """Stored baseline of query embeddings for drift comparison."""

    def __init__(self, embeddings: list[list[float]]) -> None:
        if not embeddings:
            msg = "Baseline requires at least one embedding vector."
            raise ValueError(msg)
        self.embeddings = embeddings
        self._centroid: list[float] | None = None

    @property
    def centroid(self) -> list[float]:
        """Compute the mean (centroid) of all baseline embeddings."""
        if self._centroid is not None:
            return self._centroid
        dim = len(self.embeddings[0])
        n = len(self.embeddings)
        centroid = [0.0] * dim
        for emb in self.embeddings:
            for i, val in enumerate(emb):
                centroid[i] += val
        self._centroid = [c / n for c in centroid]
        return self._centroid

    def save(self, path: str | Path) -> None:
        """Save baseline embeddings to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump({"embeddings": self.embeddings}, f)

    @classmethod
    def load(cls, path: str | Path) -> "DriftBaseline":
        """Load baseline embeddings from a JSON file."""
        path = Path(path)
        if not path.exists():
            msg = f"Baseline file not found: {path}"
            raise FileNotFoundError(msg)
        with path.open() as f:
            data = json.load(f)
        return cls(embeddings=data["embeddings"])


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """Compute cosine distance (1 - cosine_similarity) between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    return 1.0 - similarity


class DriftDetector:
    """Detects query distribution drift from a baseline.

    Computes the centroid of current query embeddings and measures
    cosine distance from the baseline centroid. Alerts when the
    distance exceeds the configured threshold (default: 0.15).
    """

    def __init__(self, threshold: float = 0.15) -> None:
        self.threshold = threshold

    def analyze(
        self,
        current_embeddings: list[list[float]],
        baseline: DriftBaseline,
    ) -> DriftReport:
        """Compare current query embeddings against the baseline."""
        if not current_embeddings:
            return DriftReport(
                baseline_distance=0.0,
                is_drifting=False,
                threshold=self.threshold,
                details="No current embeddings to analyze.",
            )

        dim = len(current_embeddings[0])
        n = len(current_embeddings)
        current_centroid = [0.0] * dim
        for emb in current_embeddings:
            for i, val in enumerate(emb):
                current_centroid[i] += val
        current_centroid = [c / n for c in current_centroid]

        distance = _cosine_distance(baseline.centroid, current_centroid)
        is_drifting = distance > self.threshold

        details = (
            f"Centroid cosine distance: {distance:.4f} "
            f"(threshold: {self.threshold:.4f}). "
            f"{'DRIFT DETECTED' if is_drifting else 'Within normal range'}. "
            f"Baseline: {len(baseline.embeddings)} vectors, Current: {n} vectors."
        )

        return DriftReport(
            baseline_distance=distance,
            is_drifting=is_drifting,
            threshold=self.threshold,
            details=details,
        )

    def save_baseline(
        self,
        embeddings: list[list[float]],
        path: str | Path,
    ) -> None:
        """Save embeddings as a new baseline."""
        baseline = DriftBaseline(embeddings=embeddings)
        baseline.save(path)
