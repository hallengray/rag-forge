"""Progress reporting for long-running audits.

Addresses a UX gap uncovered during the 2026-04-13 cycle-1 audit: users
had no idea a run would take 8-15 minutes or cost real money, and during the
run there was no indication of progress. The ``ProgressReporter`` protocol
lets the audit orchestrator emit lifecycle events which a reporter
implementation formats for the user (stderr by default) or ignores (tests).

Design notes:
- All reporter output goes to stderr. stdout is reserved for the final JSON
  report consumed by the Node CLI bridge.
- Reporters are driven by the audit pipeline, not by individual metrics, so
  a sample is "scored" after all metrics have run against it.
- The ``NullProgressReporter`` is the default so existing callers (and the
  test suite) do not need to pass one explicitly.
- **Query content is redacted by default** in streamed progress lines.
  ``stderr`` is commonly captured by CI systems, terminal recorders, and
  log collectors, so streaming raw queries could leak PHI/PII for
  clinical, legal, or financial RAG pipelines. Set
  ``RAG_FORGE_LOG_QUERIES=1`` in the environment to opt into showing
  query previews in progress output.
"""

import os
import sys
from typing import Protocol, TextIO, runtime_checkable

from rag_forge_evaluator.cost_estimates import AuditEstimate


@runtime_checkable
class ProgressReporter(Protocol):
    """Receives lifecycle events during an audit run."""

    def audit_started(
        self,
        *,
        sample_count: int,
        metric_names: list[str],
        judge_model: str,
        evaluator_engine: str,
        estimate: AuditEstimate,
    ) -> None:
        """Called once when the audit is about to start the judge loop."""

    def sample_scored(
        self,
        *,
        index: int,
        total: int,
        query_preview: str,
        metrics: dict[str, float],
        skipped_count: int,
        elapsed_seconds: float,
    ) -> None:
        """Called after a sample has been scored against every metric."""

    def audit_completed(
        self,
        *,
        elapsed_seconds: float,
        scored_count: int,
        skipped_count: int,
        overall_score: float,
        rmm_level: int,
        report_path: str | None,
    ) -> None:
        """Called once after aggregation and report generation succeed."""


class NullProgressReporter:
    """Progress reporter that silently discards every event."""

    def audit_started(self, **kwargs: object) -> None:
        return

    def sample_scored(self, **kwargs: object) -> None:
        return

    def audit_completed(self, **kwargs: object) -> None:
        return


class StderrProgressReporter:
    """Default reporter that writes human-readable progress to stderr."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stderr

    def _write(self, line: str) -> None:
        self._stream.write(line)
        self._stream.write("\n")
        self._stream.flush()

    def audit_started(
        self,
        *,
        sample_count: int,
        metric_names: list[str],
        judge_model: str,
        evaluator_engine: str,
        estimate: AuditEstimate,
    ) -> None:
        fallback_note = (
            "  (pricing unknown for this model — using the highest known model pricing "
            "as a conservative fallback)"
            if estimate.is_fallback_pricing
            else ""
        )
        banner = (
            "\n"
            "RAG-Forge Audit\n"
            "===============\n"
            f"  Samples:         {sample_count}\n"
            f"  Metrics:         {len(metric_names)} ({', '.join(metric_names)})\n"
            f"  Judge calls:     {estimate.judge_calls} total\n"
            f"  Judge model:     {judge_model}\n"
            f"  Evaluator:       {evaluator_engine}\n"
            "\n"
            f"  Estimated time:  {estimate.minutes_low:.0f}-{estimate.minutes_high:.0f} minutes\n"
            f"  Estimated cost:  ~${estimate.cost_usd:.2f} USD\n"
            f"{fallback_note}\n"
            "\n"
            "Progress will stream below. Ctrl+C to abort.\n"
            "---"
        )
        self._write(banner)

    def sample_scored(
        self,
        *,
        index: int,
        total: int,
        query_preview: str,
        metrics: dict[str, float],
        skipped_count: int,
        elapsed_seconds: float,
    ) -> None:
        width = len(str(total))
        scores_part = "  ".join(
            f"{_short_name(name)}={score:.2f}" for name, score in metrics.items()
        )
        status = "OK" if skipped_count == 0 else f"WARN {skipped_count} skipped"
        # Redact query content by default to avoid leaking PHI/PII into
        # CI logs, terminal recorders, or log collectors. Opt in with
        # RAG_FORGE_LOG_QUERIES=1 for local debugging.
        if os.environ.get("RAG_FORGE_LOG_QUERIES") == "1":
            preview = query_preview[:40].replace("\n", " ")
            if len(query_preview) > 40:
                preview = preview[:37] + "..."
        else:
            preview = "[query redacted]"
        line = (
            f"[{index:>{width}}/{total}] {preview:<40}  "
            f"{scores_part}  {status}  ({elapsed_seconds:.1f}s)"
        )
        self._write(line)

    def audit_completed(
        self,
        *,
        elapsed_seconds: float,
        scored_count: int,
        skipped_count: int,
        overall_score: float,
        rmm_level: int,
        report_path: str | None,
    ) -> None:
        minutes = int(elapsed_seconds // 60)
        seconds = int(elapsed_seconds % 60)
        self._write("---")
        self._write(f"Audit complete in {minutes}m {seconds}s")
        self._write(
            f"Scored: {scored_count} metric evaluations    "
            f"Skipped: {skipped_count} (invalid or incomplete judge outputs — see report for details)"
        )
        self._write(f"Overall: {overall_score:.4f}    RMM Level: {rmm_level}")
        if report_path:
            self._write(f"Report:  {report_path}")


def _short_name(metric_name: str) -> str:
    """Compress metric names so per-sample lines stay readable at 80 cols."""
    shortcuts = {
        "faithfulness": "faith",
        "context_relevance": "ctx",
        "answer_relevance": "ans",
        "hallucination": "hall",
    }
    return shortcuts.get(metric_name, metric_name[:5])


def confirm_or_exit(
    *,
    assume_yes: bool,
    stream: TextIO | None = None,
) -> None:
    """Prompt the user to confirm before starting the audit.

    - If ``assume_yes`` is True, returns immediately.
    - If stdin is not a TTY and ``assume_yes`` is False, exits with a clear
      error telling the caller to pass --yes for non-interactive use.
    - Otherwise prompts "Proceed? [y/N]" and exits on anything but y/yes.
    """
    if assume_yes:
        return

    out = stream if stream is not None else sys.stderr

    if not sys.stdin.isatty():
        out.write(
            "error: audit will make paid judge calls but stdin is not a TTY.\n"
            "       Pass --yes (-y) to run non-interactively.\n"
        )
        out.flush()
        sys.exit(2)

    out.write("Proceed? [y/N]: ")
    out.flush()
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        out.write("\nAborted.\n")
        out.flush()
        sys.exit(1)

    if answer not in ("y", "yes"):
        out.write("Aborted.\n")
        out.flush()
        sys.exit(1)
