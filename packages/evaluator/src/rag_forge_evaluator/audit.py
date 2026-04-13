"""Audit orchestrator: coordinates evaluation, history, and report generation."""

import time
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag_forge_evaluator.cost_estimates import estimate_audit
from rag_forge_evaluator.engine import EvaluationResult
from rag_forge_evaluator.engines import create_evaluator
from rag_forge_evaluator.history import AuditHistory, AuditHistoryEntry
from rag_forge_evaluator.input_loader import InputLoader
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.mock_judge import MockJudge
from rag_forge_evaluator.maturity import RMMLevel, RMMScorer
from rag_forge_evaluator.progress import NullProgressReporter, ProgressReporter, confirm_or_exit
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
    evaluator_engine: str = "llm-judge"
    tracer: Any = None  # opentelemetry.trace.Tracer or None
    progress: ProgressReporter | None = None
    assume_yes: bool = False


@dataclass
class AuditReport:
    """Complete audit report with evaluation results and RMM scoring."""

    evaluation: EvaluationResult
    rmm_level: RMMLevel
    report_path: Path
    json_report_path: Path
    samples_evaluated: int
    pdf_report_path: Path | None = None


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
        self._tracer = config.tracer
        self._progress: ProgressReporter = config.progress or NullProgressReporter()

    def _span(self, name: str) -> Any:
        """Return an active span context manager, or a no-op if no tracer is configured."""
        if self._tracer is not None:
            return self._tracer.start_as_current_span(name)
        return nullcontext()

    def run(self) -> AuditReport:
        """Execute the full audit pipeline."""
        with self._span("rag-forge.audit"):
            # 1. Load input
            with self._span("rag-forge.load_input") as span:
                if self.config.input_path:
                    samples = InputLoader.load_jsonl(self.config.input_path)
                    source_type = "jsonl"
                elif self.config.golden_set_path:
                    samples = InputLoader.load_golden_set(self.config.golden_set_path)
                    source_type = "golden_set"
                else:
                    msg = "Either input_path or golden_set_path must be provided"
                    raise ValueError(msg)
                if span is not None:
                    span.set_attribute("sample_count", len(samples))
                    span.set_attribute("source_type", source_type)

            # 2. Create evaluator via factory
            judge = _create_judge(self.config.judge_model)
            evaluator = create_evaluator(
                self.config.evaluator_engine,
                judge=judge,
                thresholds=self.config.thresholds,
                progress=self._progress,
            )

            # 2a. Print banner + confirm (no-op for NullProgressReporter + assume_yes).
            metric_names = evaluator.supported_metrics()
            estimate = estimate_audit(
                sample_count=len(samples),
                metric_count=len(metric_names),
                judge_model=judge.model_name(),
            )
            self._progress.audit_started(
                sample_count=len(samples),
                metric_names=metric_names,
                judge_model=judge.model_name(),
                evaluator_engine=self.config.evaluator_engine,
                estimate=estimate,
            )
            # Only prompt when the run will actually spend money. Mock and
            # local/free judges have cost_usd == 0.0 and should proceed silently
            # so existing test suites and CI runs are unaffected.
            if estimate.cost_usd > 0:
                confirm_or_exit(assume_yes=self.config.assume_yes)

            # 3. Run evaluation
            audit_start = time.monotonic()
            with self._span("rag-forge.evaluate") as span:
                evaluation = evaluator.evaluate(samples)
                if span is not None:
                    span.set_attribute("engine", self.config.evaluator_engine)
                    span.set_attribute("sample_count", evaluation.samples_evaluated)

            # 4. Score against RMM
            metric_map = {m.name: m.score for m in evaluation.metrics}
            with self._span("rag-forge.score_rmm") as span:
                rmm_level = RMMScorer().assess(metric_map)
                if span is not None:
                    span.set_attribute("rmm_level", int(rmm_level))

            # 5. Load history and compute trends
            history = AuditHistory(self.config.output_dir / "audit-history.json")
            previous = history.get_previous()
            trends = history.compute_trends(metric_map, previous)

            # 6. Generate reports
            generator = ReportGenerator(output_dir=self.config.output_dir)
            with self._span("rag-forge.generate_report") as span:
                report_path = generator.generate_html(
                    evaluation, rmm_level,
                    trends=trends,
                    sample_results=evaluation.sample_results,
                )
                json_report_path = generator.generate_json(
                    evaluation, rmm_level,
                    sample_results=evaluation.sample_results,
                )
                if span is not None:
                    span.set_attribute("report_path", str(report_path))

            # 7. Generate PDF (optional)
            pdf_report_path: Path | None = None
            if self.config.generate_pdf:
                from rag_forge_evaluator.report.pdf import PDFGenerator
                pdf_report_path = PDFGenerator().generate(report_path)

            # 8. Append to history (after all reports succeed)
            history.append(AuditHistoryEntry(
                timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                metrics=metric_map,
                rmm_level=int(rmm_level),
                overall_score=evaluation.overall_score,
                passed=evaluation.passed,
            ))

            # 9. Emit completion event.
            metric_count = len(evaluation.metrics) or 1
            total_evaluations = evaluation.samples_evaluated * metric_count
            self._progress.audit_completed(
                elapsed_seconds=time.monotonic() - audit_start,
                scored_count=total_evaluations - evaluation.skipped_evaluations,
                skipped_count=evaluation.skipped_evaluations,
                overall_score=evaluation.overall_score,
                rmm_level=int(rmm_level),
                report_path=str(report_path),
            )

            return AuditReport(
                evaluation=evaluation,
                rmm_level=rmm_level,
                report_path=report_path,
                json_report_path=json_report_path,
                samples_evaluated=evaluation.samples_evaluated,
                pdf_report_path=pdf_report_path,
            )
