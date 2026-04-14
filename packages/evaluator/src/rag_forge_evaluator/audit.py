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
from rag_forge_evaluator.judge.claude_judge import (
    OnRetryCallback,
    OverloadBudgetExhaustedError,
)
from rag_forge_evaluator.judge.mock_judge import MockJudge
from rag_forge_evaluator.maturity import RMMLevel, RMMScorer
from rag_forge_evaluator.progress import NullProgressReporter, ProgressReporter, confirm_or_exit
from rag_forge_evaluator.report.generator import ReportGenerator


def _voyageai_installed() -> bool:
    """Importability probe for voyageai. Extracted as a module-level
    function so tests can monkeypatch it without importing the real SDK.
    """
    try:
        import voyageai  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


class ConfigurationError(ValueError):
    """Raised when an AuditConfig combination is invalid or unsafe to run."""


class PartialAuditError(RuntimeError):
    """Raised when the audit loop aborted mid-run but a partial report exists.

    Wraps the triggering exception. The CLI catches this and exits with code
    3 (partial success) so CI scripts can distinguish a partial audit from a
    hard failure. The ``partial_report_path`` is always a written file — the
    orchestrator only raises this after the partial JSON has hit disk.
    """

    def __init__(
        self,
        partial_report_path: Path,
        completed_samples: int,
        total_samples: int,
        aborted_reason: str,
        original: BaseException,
    ) -> None:
        super().__init__(
            f"Audit aborted at sample {completed_samples}/{total_samples} "
            f"({aborted_reason}). Partial report: {partial_report_path}"
        )
        self.partial_report_path = partial_report_path
        self.completed_samples = completed_samples
        self.total_samples = total_samples
        self.aborted_reason = aborted_reason
        self.original = original


@dataclass
class AuditConfig:
    """Configuration for an audit run."""

    input_path: Path | None = None
    golden_set_path: Path | None = None
    judge_model: str | None = None
    judge_model_name: str | None = None  # specific model id passed to the provider
    output_dir: Path = Path("./reports")
    generate_pdf: bool = False
    thresholds: dict[str, float] | None = None
    evaluator_engine: str = "llm-judge"
    tracer: Any = None  # opentelemetry.trace.Tracer or None
    progress: ProgressReporter | None = None
    assume_yes: bool = False
    on_judge_retry: OnRetryCallback | None = None
    refusal_aware: bool = True
    ragas_max_tokens: int = 8192
    ragas_embeddings_provider: str | None = None  # None = auto-select from judge type


@dataclass
class AuditReport:
    """Complete audit report with evaluation results and RMM scoring."""

    evaluation: EvaluationResult
    rmm_level: RMMLevel
    report_path: Path
    json_report_path: Path
    samples_evaluated: int
    pdf_report_path: Path | None = None


_KNOWN_JUDGE_ALIASES = ("mock", "claude", "claude-sonnet", "openai", "gpt-4o")


def _create_judge(
    model: str | None,
    model_name: str | None = None,
    on_retry: OnRetryCallback | None = None,
) -> JudgeProvider:
    """Create a judge provider based on provider alias and optional model id.

    Args:
        model: Provider alias - "mock", "claude", "claude-sonnet", "openai",
            "gpt-4o". Determines which judge class to instantiate. Unknown
            aliases raise ConfigurationError so typos like "claud" fail
            loudly instead of silently downgrading to a free mock run.
        model_name: Specific model identifier passed through to the judge
            constructor (e.g. "claude-opus-4-6", "gpt-4-turbo"). When None,
            the judge falls back to its env-var/default model.
        on_retry: Optional callback invoked when ClaudeJudge retries a 529
            Overloaded error. Ignored for non-Claude judges.
    """
    if model == "mock" or model is None:
        return MockJudge()
    if model in ("claude", "claude-sonnet"):
        from rag_forge_evaluator.judge.claude_judge import ClaudeJudge
        return ClaudeJudge(model=model_name, on_retry=on_retry)
    if model in ("openai", "gpt-4o"):
        from rag_forge_evaluator.judge.openai_judge import OpenAIJudge
        return OpenAIJudge(model=model_name)
    msg = (
        f"Unknown judge provider {model!r}. Expected one of: "
        f"{', '.join(repr(a) for a in _KNOWN_JUDGE_ALIASES)}. "
        "Did you mean 'claude' or 'openai'?"
    )
    raise ConfigurationError(msg)


class AuditOrchestrator:
    """Orchestrates the full audit pipeline."""

    def __init__(self, config: AuditConfig) -> None:
        self._validate_config(config)
        self.config = config
        self._tracer = config.tracer
        self._progress: ProgressReporter = config.progress or NullProgressReporter()

    @staticmethod
    def _validate_config(config: AuditConfig) -> None:
        """Reject unsafe combinations before any judge calls happen.

        In v0.2.0 we permit ``--evaluator ragas --judge claude`` — the
        RAGAS engine now injects a RagForgeRagasLLM wrapper that honors
        the configured judge end-to-end. The remaining constraint is
        that Claude + ragas requires Voyage embeddings (installed via
        the ``[ragas-voyage]`` extra), because ragas needs an embeddings
        provider and we do not want to silently fall back to OpenAI
        when the user picked an Anthropic-native stack.
        """
        if config.evaluator_engine == "ragas":
            judge = config.judge_model
            if judge not in ("openai", "gpt-4o", "claude", "mock"):
                msg = (
                    f"--evaluator ragas does not support --judge {judge!r}. "
                    "Use claude, openai, or mock."
                )
                raise ConfigurationError(msg)
            if judge == "claude" and not _voyageai_installed():
                msg = (
                    "--evaluator ragas --judge claude requires Voyage embeddings. "
                    "Install with: pip install rag-forge-evaluator[ragas-voyage]\n"
                    "Alternatively, pass --judge openai to use OpenAI embeddings."
                )
                raise ConfigurationError(msg)

    def _span(self, name: str) -> Any:
        """Return an active span context manager, or a no-op if no tracer is configured."""
        if self._tracer is not None:
            return self._tracer.start_as_current_span(name)
        return nullcontext()

    def run(self) -> AuditReport:
        """Execute the full audit pipeline."""
        # 0. Fail fast on missing optional deps before any judge calls run.
        if self.config.generate_pdf:
            from rag_forge_evaluator.report.pdf import is_available

            ok, error = is_available()
            if not ok:
                msg = (
                    f"--pdf was requested but PDF generation is unavailable: {error}. "
                    f"Re-run without --pdf or install the [pdf] extra before starting "
                    f"the audit (judge calls are expensive)."
                )
                raise ConfigurationError(msg)

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
            judge = _create_judge(
                self.config.judge_model,
                self.config.judge_model_name,
                on_retry=self.config.on_judge_retry,
            )
            evaluator = create_evaluator(
                self.config.evaluator_engine,
                judge=judge,
                thresholds=self.config.thresholds,
                progress=self._progress,
            )

            # 2a. Print banner + confirm (no-op for NullProgressReporter + assume_yes).
            metric_names = evaluator.supported_metrics()
            estimate_model = judge.model_name()
            banner_judge_model = judge.model_name()
            estimate = estimate_audit(
                sample_count=len(samples),
                metric_count=len(metric_names),
                judge_model=estimate_model,
            )
            self._progress.audit_started(
                sample_count=len(samples),
                metric_names=metric_names,
                judge_model=banner_judge_model,
                evaluator_engine=self.config.evaluator_engine,
                estimate=estimate,
            )
            # Only prompt when the run will actually spend money. Mock and
            # local/free judges have cost_usd == 0.0 and should proceed silently
            # so existing test suites and CI runs are unaffected.
            if estimate.cost_usd > 0:
                confirm_or_exit(assume_yes=self.config.assume_yes)

            # 3. Run evaluation — wrap in a mid-loop abort guard so that a
            # crash or Ctrl+C mid-way through a long audit still produces a
            # partial report with everything scored so far. The alternative
            # (losing 40 minutes of judge spend because sample 41 of 50
            # crashed) is unacceptable for paid runs.
            audit_start = time.monotonic()
            try:
                with self._span("rag-forge.evaluate") as span:
                    evaluation = evaluator.evaluate(samples)
                    if span is not None:
                        span.set_attribute("engine", self.config.evaluator_engine)
                        span.set_attribute("sample_count", evaluation.samples_evaluated)
            except (Exception, KeyboardInterrupt) as exc:
                partial_path = self._maybe_write_partial_report(
                    evaluator=evaluator,
                    total_samples=len(samples),
                    exc=exc,
                )
                if partial_path is None:
                    raise
                completed = len(getattr(evaluator, "partial_sample_results", []))
                raise PartialAuditError(
                    partial_report_path=partial_path,
                    completed_samples=completed,
                    total_samples=len(samples),
                    aborted_reason=_classify_abort(exc),
                    original=exc,
                ) from exc

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
            metric_count = len(evaluation.metrics)
            total_evaluations = evaluation.samples_evaluated * metric_count
            self._progress.audit_completed(
                elapsed_seconds=time.monotonic() - audit_start,
                scored_count=max(total_evaluations - evaluation.skipped_evaluations, 0),
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

    def _maybe_write_partial_report(
        self,
        evaluator: Any,
        total_samples: int,
        exc: BaseException,
    ) -> Path | None:
        """Flush whatever has been scored so far to audit-report.partial.json.

        Returns the path to the partial report, or None if the evaluator
        doesn't expose partial state (e.g. the RAGAS engine, which batches
        internally and has no mid-loop hook). Never raises — a failure here
        would shadow the real exception the caller is about to re-raise.
        """
        partial = getattr(evaluator, "partial_sample_results", None)
        if not partial:
            return None
        try:
            aggregates_fn = getattr(evaluator, "compute_partial_aggregates", None)
            partial_metrics = aggregates_fn() if callable(aggregates_fn) else {}
            generator = ReportGenerator(output_dir=self.config.output_dir)
            return generator.generate_partial_json(
                sample_results=partial,
                total_samples=total_samples,
                aborted_reason=_classify_abort(exc),
                partial_metrics=partial_metrics,
                error_message=f"{type(exc).__name__}: {exc}",
            )
        except Exception:
            return None


def _classify_abort(exc: BaseException) -> str:
    """Translate an exception into a short, machine-readable abort reason."""
    if isinstance(exc, KeyboardInterrupt):
        return "keyboard_interrupt"
    if isinstance(exc, OverloadBudgetExhaustedError):
        return "retry_budget_exhausted"
    return "unhandled_exception"
