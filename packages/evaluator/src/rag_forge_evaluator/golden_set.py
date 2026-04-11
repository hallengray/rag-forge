"""Golden set management: load, validate, and manage evaluation datasets."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GoldenSetEntry:
    """A single entry in the golden set."""

    query: str
    expected_answer_keywords: list[str]
    expected_source_chunk_ids: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    topic: str = "general"
    requires_multi_hop: bool = False
    adversarial: bool = False


class GoldenSet:
    """Manages golden set datasets for evaluation."""

    def __init__(self) -> None:
        self.entries: list[GoldenSetEntry] = []

    def load(self, path: str | Path) -> None:
        """Load a golden set from a JSON file."""
        # Stub: full implementation in Phase 1
        _ = path

    def validate(self) -> list[str]:
        """Check golden set for coverage, balance, and schema compliance."""
        errors: list[str] = []
        if not self.entries:
            errors.append("Golden set is empty")
        return errors
