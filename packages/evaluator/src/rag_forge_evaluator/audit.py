"""Audit orchestrator: coordinates evaluation and report generation."""

from dataclasses import dataclass
from pathlib import Path

from rag_forge_evaluator.engine import EvaluationResult
from rag_forge_evaluator.input_loader import InputLoader
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.mock_judge import MockJudge
from rag_forge_evaluator.maturity import RMMLevel, RMMScorer
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator
from rag_forge_evaluator.report.generator import ReportGenerator


@dataclass
class AuditConfig:
    """Configuration for an audit run."""

    input_path: Path | None = None
    golden_set_path: Path | None = None
    judge_model: str | None = None
    output_dir: Path = Path("./reports")
    generate_pdf: bool = False
    thresholds: dict[str, float] | None = None


@dataclass
class AuditReport:
    """Complete audit report with evaluation results and RMM scoring."""

    evaluation: EvaluationResult
    rmm_level: RMMLevel
    report_path: Path
    samples_evaluated: int


def _create_judge(model: str | None) -> JudgeProvider:
    """Create a judge provider based on model name."""
    if model == "mock" or model is None:
        return MockJudge()
    if model in ("claude", "claude-sonnet"):
        from rag_forge_evaluator.judge.claude_judge import ClaudeJudge
        return ClaudeJudge()
    if model in ("openai", "gpt-4o"):
        from rag_forge_evaluator.judge.openai_judge import OpenAIJudge
        return OpenAIJudge()
    return MockJudge()


class AuditOrchestrator:
    """Orchestrates the full audit pipeline."""

    def __init__(self, config: AuditConfig) -> None:
        self.config = config

    def run(self) -> AuditReport:
        """Execute the full audit pipeline."""
        # 1. Load input
        if self.config.input_path:
            samples = InputLoader.load_jsonl(self.config.input_path)
        elif self.config.golden_set_path:
            samples = InputLoader.load_golden_set(self.config.golden_set_path)
        else:
            msg = "Either input_path or golden_set_path must be provided"
            raise ValueError(msg)

        # 2. Create judge and evaluator
        judge = _create_judge(self.config.judge_model)
        evaluator = LLMJudgeEvaluator(judge=judge, thresholds=self.config.thresholds)

        # 3. Run evaluation
        evaluation = evaluator.evaluate(samples)

        # 4. Score against RMM
        metric_map = {m.name: m.score for m in evaluation.metrics}
        rmm_level = RMMScorer().assess(metric_map)

        # 5. Generate report
        generator = ReportGenerator(output_dir=self.config.output_dir)
        report_path = generator.generate_html(evaluation, rmm_level)

        return AuditReport(
            evaluation=evaluation,
            rmm_level=rmm_level,
            report_path=report_path,
            samples_evaluated=evaluation.samples_evaluated,
        )
