"""Load evaluation inputs from JSONL telemetry files or golden set JSON."""

import json
import logging
from pathlib import Path

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.golden_set import GoldenSetEntry

logger = logging.getLogger(__name__)

_REQUIRED_JSONL_FIELDS = {"query", "contexts", "response"}


class InputLoader:
    """Loads evaluation samples from JSONL or golden set files."""

    @staticmethod
    def load_jsonl(path: Path) -> list[EvaluationSample]:
        """Load samples from a JSONL telemetry file. Skips malformed lines."""
        samples: list[EvaluationSample] = []
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return samples

        for line_num, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON at line %d", line_num)
                continue

            if not isinstance(data, dict) or not _REQUIRED_JSONL_FIELDS.issubset(data.keys()):
                logger.warning("Skipping line %d: missing required fields", line_num)
                continue

            sample_id = (
                data.get("case_id")
                or data.get("sample_id")
                or data.get("id")
                or f"sample-{line_num:03d}"
            )

            samples.append(
                EvaluationSample(
                    query=data["query"],
                    contexts=data["contexts"],
                    response=data["response"],
                    expected_answer=data.get("expected_answer"),
                    chunk_ids=data.get("chunk_ids"),
                    sample_id=sample_id,
                )
            )
        return samples

    @staticmethod
    def load_golden_set(path: Path) -> list[EvaluationSample]:
        """Load samples from a golden set JSON file."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []

        samples: list[EvaluationSample] = []
        for item in raw:
            try:
                entry = GoldenSetEntry(**item)
            except (TypeError, ValueError):
                logger.warning("Skipping invalid golden set entry: %s", item)
                continue

            samples.append(
                EvaluationSample(
                    query=entry.query,
                    contexts=[],
                    response="",
                    expected_answer=", ".join(entry.expected_answer_keywords),
                )
            )
        return samples
