"""Audit history tracking for trend analysis."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AuditHistoryEntry:
    timestamp: str
    metrics: dict[str, float]
    rmm_level: int
    overall_score: float
    passed: bool


class AuditHistory:
    def __init__(self, history_path: Path) -> None:
        self._path = history_path

    def load(self) -> list[AuditHistoryEntry]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return [AuditHistoryEntry(**entry) for entry in data]

    def append(self, entry: AuditHistoryEntry) -> None:
        entries = self.load()
        entries.append(entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to temp file then rename
        tmp_path = self._path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps([asdict(e) for e in entries], indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self._path)

    def get_previous(self) -> AuditHistoryEntry | None:
        entries = self.load()
        return entries[-1] if entries else None

    def compute_trends(self, current: dict[str, float], previous: AuditHistoryEntry | None) -> dict[str, str]:
        if previous is None:
            return {}
        trends: dict[str, str] = {}
        for metric, score in current.items():
            prev_score = previous.metrics.get(metric)
            if prev_score is None:
                trends[metric] = "→"
            elif score - prev_score >= 0.02:
                trends[metric] = "↑"
            elif prev_score - score >= 0.02:
                trends[metric] = "↓"
            else:
                trends[metric] = "→"
        return trends
