"""Tests for progress reporting and cost estimation (Task 0)."""

import io

import pytest

from rag_forge_evaluator.cost_estimates import estimate_audit
from rag_forge_evaluator.progress import (
    NullProgressReporter,
    ProgressReporter,
    StderrProgressReporter,
    confirm_or_exit,
)

# ---------- cost_estimates ----------


def test_estimate_known_model_uses_table_pricing() -> None:
    est = estimate_audit(sample_count=19, metric_count=4, judge_model="claude-sonnet-4-20250514")
    assert est.judge_calls == 76
    assert est.is_fallback_pricing is False
    # 76 calls * (1500 in + 800 out) tokens = 114000 in + 60800 out
    # At $3/MTok in + $15/MTok out: 0.342 + 0.912 = 1.254 (unrounded)
    assert est.cost_usd == pytest.approx(1.254, abs=0.001)
    assert est.minutes_low < est.minutes_high
    assert est.minutes_low > 0


def test_estimate_unknown_model_uses_conservative_max_pricing() -> None:
    """Unknown models should over-estimate, not under-estimate."""
    est = estimate_audit(sample_count=10, metric_count=4, judge_model="unknown-model")
    assert est.is_fallback_pricing is True
    # The most expensive known model under (1500 in + 800 out) is opus
    # at ($15 in + $75 out per MTok). 40 calls x (1500*15 + 800*75) / 1M = 3.3
    # That should be MORE expensive than gpt-4o would have estimated (0.66).
    gpt4o_est = estimate_audit(sample_count=10, metric_count=4, judge_model="gpt-4o")
    assert est.cost_usd > gpt4o_est.cost_usd


def test_estimate_cost_is_unrounded_at_source() -> None:
    """Tiny costs must survive the cost gate, not get rounded to 0.00."""
    # 1 sample x 4 metrics x 1500 in x $0.15/MTok + 4 x 800 x $0.60/MTok = $0.0027
    est = estimate_audit(sample_count=1, metric_count=4, judge_model="gpt-4o-mini")
    assert est.cost_usd > 0
    assert est.cost_usd < 0.01  # tiny but non-zero
    # The orchestrator's cost gate is `if estimate.cost_usd > 0`; this must hold.


def test_estimate_unknown_model_falls_back_and_flags() -> None:
    est = estimate_audit(sample_count=10, metric_count=4, judge_model="gemini-2.5-pro")
    assert est.is_fallback_pricing is True
    assert est.judge_calls == 40
    assert est.cost_usd > 0


def test_estimate_mock_model_is_free() -> None:
    est = estimate_audit(sample_count=19, metric_count=4, judge_model="mock")
    assert est.cost_usd == 0.0
    assert est.is_fallback_pricing is False


# ---------- NullProgressReporter ----------


def test_null_reporter_accepts_all_events_silently() -> None:
    reporter = NullProgressReporter()
    reporter.audit_started(
        sample_count=1,
        metric_names=["faithfulness"],
        judge_model="mock",
        evaluator_engine="llm-judge",
        estimate=estimate_audit(sample_count=1, metric_count=1, judge_model="mock"),
    )
    reporter.sample_scored(
        index=1,
        total=1,
        query_preview="q",
        metrics={"faithfulness": 0.9},
        skipped_count=0,
        elapsed_seconds=1.0,
    )
    reporter.audit_completed(
        elapsed_seconds=1.0,
        scored_count=1,
        skipped_count=0,
        overall_score=0.9,
        rmm_level=1,
        report_path="x.html",
    )


def test_null_reporter_implements_protocol() -> None:
    assert isinstance(NullProgressReporter(), ProgressReporter)


# ---------- StderrProgressReporter ----------


def test_stderr_reporter_writes_banner_with_key_fields() -> None:
    buf = io.StringIO()
    reporter = StderrProgressReporter(stream=buf)
    est = estimate_audit(sample_count=19, metric_count=4, judge_model="claude-sonnet-4-20250514")
    reporter.audit_started(
        sample_count=19,
        metric_names=["faithfulness", "context_relevance", "answer_relevance", "hallucination"],
        judge_model="claude-sonnet-4-20250514",
        evaluator_engine="llm-judge",
        estimate=est,
    )
    out = buf.getvalue()
    assert "RAG-Forge Audit" in out
    assert "Samples:         19" in out
    assert "Judge calls:     76" in out
    assert "claude-sonnet-4-20250514" in out
    assert "llm-judge" in out
    assert "Estimated cost:" in out
    assert "Ctrl+C to abort" in out


def test_stderr_reporter_flags_fallback_pricing_in_banner() -> None:
    buf = io.StringIO()
    reporter = StderrProgressReporter(stream=buf)
    est = estimate_audit(sample_count=5, metric_count=4, judge_model="unknown-model-xyz")
    reporter.audit_started(
        sample_count=5,
        metric_names=["faithfulness", "context_relevance", "answer_relevance", "hallucination"],
        judge_model="unknown-model-xyz",
        evaluator_engine="llm-judge",
        estimate=est,
    )
    assert "pricing unknown" in buf.getvalue()


def test_stderr_reporter_redacts_query_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """PHI/PII protection: query content must NOT appear in default stderr output."""
    monkeypatch.delenv("RAG_FORGE_LOG_QUERIES", raising=False)
    buf = io.StringIO()
    reporter = StderrProgressReporter(stream=buf)
    sensitive = "Patient John Doe SSN 123-45-6789 with chest pain at 52 years old"
    reporter.sample_scored(
        index=1,
        total=19,
        query_preview=sensitive,
        metrics={
            "faithfulness": 0.92,
            "context_relevance": 0.88,
            "answer_relevance": 0.91,
            "hallucination": 0.95,
        },
        skipped_count=0,
        elapsed_seconds=6.2,
    )
    line = buf.getvalue()
    assert "[query redacted]" in line
    assert "John Doe" not in line
    assert "SSN" not in line
    assert "123-45-6789" not in line
    # Scores still visible so progress is meaningful.
    assert "faith=0.92" in line
    assert "OK" in line
    assert "6.2s" in line


def test_stderr_reporter_shows_query_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """RAG_FORGE_LOG_QUERIES=1 enables the old preview behavior for local debugging."""
    monkeypatch.setenv("RAG_FORGE_LOG_QUERIES", "1")
    buf = io.StringIO()
    reporter = StderrProgressReporter(stream=buf)
    reporter.sample_scored(
        index=1,
        total=19,
        query_preview="Adult male, 52 years old, presents with central crushing chest pain",
        metrics={"faithfulness": 0.92},
        skipped_count=0,
        elapsed_seconds=6.2,
    )
    line = buf.getvalue()
    assert "Adult male" in line
    assert "[query redacted]" not in line


def test_stderr_reporter_shows_skipped_warning() -> None:
    buf = io.StringIO()
    reporter = StderrProgressReporter(stream=buf)
    reporter.sample_scored(
        index=2,
        total=19,
        query_preview="meningitis presentation",
        metrics={"faithfulness": 0.0, "context_relevance": 0.0},
        skipped_count=2,
        elapsed_seconds=11.4,
    )
    assert "WARN 2 skipped" in buf.getvalue()


def test_stderr_reporter_summary_includes_rmm_and_path() -> None:
    buf = io.StringIO()
    reporter = StderrProgressReporter(stream=buf)
    reporter.audit_completed(
        elapsed_seconds=563.0,
        scored_count=72,
        skipped_count=4,
        overall_score=0.6823,
        rmm_level=1,
        report_path="eval/reports/run-2026-04-13/audit-report.html",
    )
    out = buf.getvalue()
    assert "9m 23s" in out
    assert "Scored: 72" in out
    assert "Skipped: 4" in out
    # Wording covers both parse failures AND incomplete judge outputs.
    assert "invalid or incomplete" in out
    assert "0.6823" in out
    assert "RMM Level: 1" in out
    assert "audit-report.html" in out


# ---------- confirm_or_exit ----------


def test_confirm_or_exit_noops_when_assume_yes() -> None:
    buf = io.StringIO()
    confirm_or_exit(assume_yes=True, stream=buf)
    assert buf.getvalue() == ""


def test_confirm_or_exit_fails_on_non_tty_without_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeStdin:
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr("sys.stdin", _FakeStdin())
    buf = io.StringIO()
    with pytest.raises(SystemExit) as exc:
        confirm_or_exit(assume_yes=False, stream=buf)
    assert exc.value.code == 2
    assert "not a TTY" in buf.getvalue()


def test_confirm_or_exit_accepts_yes_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeStdin:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", _FakeStdin())
    monkeypatch.setattr("builtins.input", lambda: "y")
    buf = io.StringIO()
    confirm_or_exit(assume_yes=False, stream=buf)
    assert "Proceed?" in buf.getvalue()


def test_confirm_or_exit_aborts_on_no_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeStdin:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", _FakeStdin())
    monkeypatch.setattr("builtins.input", lambda: "n")
    buf = io.StringIO()
    with pytest.raises(SystemExit) as exc:
        confirm_or_exit(assume_yes=False, stream=buf)
    assert exc.value.code == 1
    assert "Aborted" in buf.getvalue()
