"""Audit orchestrator: coordinates evaluation and report generation."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AuditConfig:
    """Configuration for an audit run."""

    input_path: Path | None = None
    golden_set_path: Path | None = None
    judge_model: str | None = None
    output_dir: Path = Path("./reports")
    generate_pdf: bool = False


class AuditOrchestrator:
    """Orchestrates the full audit pipeline.

    1. Load telemetry data (JSONL) or golden set
    2. Run evaluation metrics
    3. Score against RMM
    4. Generate HTML report
    5. Optionally generate PDF via Playwright
    """

    def __init__(self, config: AuditConfig) -> None:
        self.config = config

    def run(self) -> dict[str, float]:
        """Execute the full audit pipeline."""
        # Stub: full implementation in Phase 1
        return {"status": 0.0}
