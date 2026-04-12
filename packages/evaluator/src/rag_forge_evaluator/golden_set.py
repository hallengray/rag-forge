"""Golden set management: load, validate, save, and build evaluation datasets.

Golden sets are curated question-answer pairs used to evaluate RAG pipeline quality.
The --from-traffic flag enables sampling entries from production telemetry JSONL.
"""

import json
import random
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
        path = Path(path)
        if not path.exists():
            msg = f"Golden set file not found: {path}"
            raise FileNotFoundError(msg)

        with path.open() as f:
            data = json.load(f)

        raw_entries = data.get("entries", [])
        self.entries = [
            GoldenSetEntry(
                query=e["query"],
                expected_answer_keywords=e.get("expected_answer_keywords", []),
                expected_source_chunk_ids=e.get("expected_source_chunk_ids", []),
                difficulty=e.get("difficulty", "medium"),
                topic=e.get("topic", "general"),
                requires_multi_hop=e.get("requires_multi_hop", False),
                adversarial=e.get("adversarial", False),
            )
            for e in raw_entries
        ]

    def save(self, path: str | Path) -> None:
        """Save the golden set to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "entries": [
                {
                    "query": e.query,
                    "expected_answer_keywords": e.expected_answer_keywords,
                    "expected_source_chunk_ids": e.expected_source_chunk_ids,
                    "difficulty": e.difficulty,
                    "topic": e.topic,
                    "requires_multi_hop": e.requires_multi_hop,
                    "adversarial": e.adversarial,
                }
                for e in self.entries
            ]
        }

        with path.open("w") as f:
            json.dump(data, f, indent=2)

    def add_entry(
        self,
        query: str,
        expected_answer_keywords: list[str],
        expected_source_chunk_ids: list[str] | None = None,
        difficulty: str = "medium",
        topic: str = "general",
        requires_multi_hop: bool = False,
        adversarial: bool = False,
    ) -> None:
        """Add a single entry to the golden set."""
        self.entries.append(
            GoldenSetEntry(
                query=query,
                expected_answer_keywords=expected_answer_keywords,
                expected_source_chunk_ids=expected_source_chunk_ids or [],
                difficulty=difficulty,
                topic=topic,
                requires_multi_hop=requires_multi_hop,
                adversarial=adversarial,
            )
        )

    def add_from_traffic(self, jsonl_path: str | Path, sample_size: int = 10) -> int:
        """Sample entries from production telemetry JSONL.

        Each JSONL line must have: {"query": "...", "contexts": [...], "response": "..."}
        Sampled queries are added with empty keywords (to be filled by human review).

        Returns:
            Number of entries added.
        """
        path = Path(jsonl_path)
        lines: list[dict[str, str | list[str]]] = []

        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if "query" in entry:
                        lines.append(entry)
                except json.JSONDecodeError:
                    continue

        if not lines:
            return 0

        sampled = random.sample(lines, min(sample_size, len(lines)))

        for item in sampled:
            self.entries.append(
                GoldenSetEntry(
                    query=str(item["query"]),
                    expected_answer_keywords=[],
                    difficulty="medium",
                    topic="traffic-sampled",
                )
            )

        return len(sampled)

    def validate(self) -> list[str]:
        """Check golden set for coverage, balance, and schema compliance."""
        errors: list[str] = []

        if not self.entries:
            errors.append("Golden set is empty")
            return errors

        # Duplicate queries
        queries = [e.query for e in self.entries]
        seen: set[str] = set()
        for q in queries:
            if q in seen:
                errors.append(f"Duplicate query found: '{q}'")
            seen.add(q)

        # Missing keywords
        for i, entry in enumerate(self.entries):
            if not entry.expected_answer_keywords:
                errors.append(
                    f"Entry {i} ('{entry.query[:50]}...') has no expected_answer_keywords"
                )

        # Topic balance
        topics = [e.topic for e in self.entries]
        unique_topics = set(topics)
        if len(unique_topics) == 1 and len(self.entries) >= 5:
            errors.append(
                f"All {len(self.entries)} entries have the same topic '{topics[0]}'. "
                "Consider adding topic balance for better coverage."
            )

        return errors
