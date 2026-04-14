"""HTML and JSON audit report generator.

Public surface
--------------
``generate_html(report, *, project_name, ...)`` — module-level function that
  builds a Jinja context dict from an ``EvaluationResult`` and renders
  ``audit.html.j2``, returning a complete HTML string.

``ReportGenerator`` — class-based API preserved for backward compatibility with
  ``audit.py`` and the CLI. Its ``generate_html`` and ``generate_json`` methods
  delegate to the module-level helpers and write files to disk.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from rag_forge_evaluator.engine import EvaluationResult, SampleResult, SkipRecord
from rag_forge_evaluator.maturity import RMM_CRITERIA, RMMLevel, RMMScorer

if TYPE_CHECKING:
    pass  # CostSummary is not a real type yet; we accept None or any duck-typed object

# ---------------------------------------------------------------------------
# Jinja environment — loaded once at import time.
# PackageLoader resolves relative to the installed package, not the filesystem,
# so it works correctly both in editable installs and after `pip install`.
# ---------------------------------------------------------------------------
_ENV = Environment(
    loader=PackageLoader("rag_forge_evaluator", "report/templates"),
    undefined=StrictUndefined,
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_REGULATORY_ALIGNMENT_HTML = (
    "This audit aligns with evaluation guidance from: "
    "<strong>NIST AI Risk Management Framework (AI RMF 1.0)</strong> § 4.3 Measure · "
    "<strong>ISO/IEC 42001:2023</strong> AI Management System § 8.3 Operational planning and control · "
    "<strong>EU AI Act Article 15</strong> accuracy, robustness and cybersecurity testing. "
    "Retrieval-augmented generation systems in regulated industries should be re-audited after any "
    "material change to the knowledge base, retrieval strategy, generation prompt, or judge model."
)

_RMM_EXPLANATIONS: dict[int, str] = {
    0: (
        "Your pipeline is at the Naive RAG stage — basic retrieval and generation work but haven't "
        "been optimized. To advance to Level 1, ensure hybrid search returns relevant chunks and "
        "generation stays on-topic."
    ),
    1: (
        "Your pipeline has cleared the Naive RAG stage and retrieves relevant chunks reliably. "
        "To advance to Level 2 (Better Precision), faithfulness must reach 0.85 and "
        "context-relevance must reach 0.80."
    ),
    2: (
        "Your pipeline retrieves with precision — reranking and parent-document expansion are "
        "paying off. To advance to Level 3 (Better Trust), faithfulness must reach 0.85 and "
        "hallucination must reach 0.95."
    ),
    3: (
        "Your pipeline has trust guardrails — faithfulness and hallucination are within tolerance. "
        "To advance to Level 4 (Better Workflow), add caching, cost tracking, and keep P95 "
        "latency under 4 seconds."
    ),
    4: (
        "Your pipeline is production-grade with workflow hardening. To advance to Level 5 "
        "(Enterprise), add drift detection, CI/CD regression gates, and adversarial testing."
    ),
    5: (
        "Your pipeline meets Enterprise maturity. Continue regular re-audits after material changes."
    ),
}

_METRIC_DESCRIPTIONS: dict[str, str] = {
    "faithfulness": "Does the answer stay true to the retrieved sources?",
    "answer_relevance": "Does the answer address what was asked?",
    "answer_relevancy": "Does the answer address what was asked?",
    "context_relevance": "Were the retrieved chunks actually useful?",
    "context_precision": "Were the retrieved chunks actually useful?",
    "context_recall": "Did we retrieve everything the answer needed?",
    "hallucination": "Did the answer invent facts not in the sources?",
}

_RMM_LEVEL_NAMES: dict[int, str] = {
    int(c.level): c.name for c in RMM_CRITERIA
}

# ---------------------------------------------------------------------------
# Internal pure helpers — all unit-testable, zero I/O
# ---------------------------------------------------------------------------


def _compute_rmm_summary(report: EvaluationResult) -> tuple[int, str, str]:
    """Return ``(level_number, level_name, explanation_html)`` for the report.

    Uses ``RMMScorer`` from ``maturity.py`` to compute the numeric level so
    the scoring logic stays in one place.
    """
    metric_map = {m.name: m.score for m in report.metrics}
    level: RMMLevel = RMMScorer().assess(metric_map)
    level_number = int(level)
    level_name = _RMM_LEVEL_NAMES.get(level_number, "Unknown")
    explanation = _RMM_EXPLANATIONS.get(level_number, "")
    return level_number, level_name, explanation


def _build_tldr(report: EvaluationResult) -> dict:
    """Build the TL;DR box dict from passing/failing metrics.

    Returns:
        ``{working: list[str], needs_fixing: list[str], priority_next_step_html: str}``
    """
    working: list[str] = []
    needs_fixing: list[str] = []
    worst_metric: str | None = None
    worst_gap: float = -1.0

    for m in report.metrics:
        display = m.name.replace("_", " ").title()
        if m.passed:
            working.append(f"{display} passed ({m.score:.2f} ≥ {m.threshold:.2f})")
        else:
            gap = m.threshold - m.score
            needs_fixing.append(
                f"{display} {m.score:.2f} / {m.threshold:.2f} (gap: {gap:.2f})"
            )
            if gap > worst_gap:
                worst_gap = gap
                worst_metric = m.name

    if not working:
        working.append("No metrics passed in this run.")

    if not needs_fixing:
        priority_next = "All metrics are passing. Schedule a re-audit after the next material change."
    elif worst_metric:
        # Find the sample with the largest gap on that metric
        worst_sample_id: str | None = None
        worst_sample_score = 1.0
        for sr in report.sample_results:
            score = sr.metrics.get(worst_metric)
            if score is not None and score < worst_sample_score:
                worst_sample_score = score
                worst_sample_id = sr.sample_id or "(unknown)"

        display_metric = worst_metric.replace("_", " ").title()
        priority_next = (
            f"Focus on <strong>{display_metric}</strong> (gap {worst_gap:.2f}). "
        )
        if worst_sample_id:
            priority_next += (
                f"Start with sample <code>{worst_sample_id}</code> "
                f"(score {worst_sample_score:.2f}) — it shows the largest deviation."
            )
    else:
        priority_next = "Review the failing metrics and address the largest gap first."

    return {
        "working": working,
        "needs_fixing": needs_fixing,
        "priority_next_step_html": priority_next,
    }


def _build_ladder(current_level: int) -> list[dict]:
    """Return six ladder-cell dicts with state ``cleared`` / ``current`` / ``next`` / ``future``."""
    cells: list[dict] = []
    for i in range(6):
        if i < current_level:
            state = "cleared"
        elif i == current_level:
            state = "current"
        elif i == current_level + 1:
            state = "next"
        else:
            state = "future"
        cells.append({
            "number": i,
            "name": _RMM_LEVEL_NAMES.get(i, f"Level {i}"),
            "state": state,
        })
    return cells


def _build_refusals(report: EvaluationResult) -> dict:
    """Compute refusal rate and per-case detail.

    Warns when rate > 30%.
    """
    total = report.samples_evaluated or 1  # guard against divide-by-zero
    refusal_count = report.scoring_modes_count.get("safety_refusal", 0)
    refusal_rate = refusal_count / total

    rate_percent = str(round(refusal_rate * 100))

    warn = refusal_rate > 0.30
    warning_text = (
        "Review classifications in the per-sample detail section below. "
        "Spot-check the judge's justifications to confirm they were valid safety refusals."
        if warn
        else ""
    )

    cases: list[dict] = []
    for sr in report.sample_results:
        if sr.scoring_mode == "safety_refusal":
            cases.append({
                "case_id": sr.sample_id or "(unknown)",
                "query": sr.query,
                "justification": sr.refusal_justification or "No justification recorded.",
            })

    return {
        "count": refusal_count,
        "total": report.samples_evaluated,
        "rate_percent": rate_percent,
        "warn": warn,
        "warning_text": warning_text,
        "cases": cases,
    }


def _build_worst_case(report: EvaluationResult) -> dict:
    """Find the sample with the single lowest metric score.

    Returns a dict with ``sample_id``, ``headline_metrics``, and ``diagnosis_html``.
    """
    if not report.sample_results:
        return {
            "sample_id": "n/a",
            "headline_metrics": "No sample results available.",
            "diagnosis_html": "No samples were evaluated.",
        }

    worst_sr: SampleResult | None = None
    worst_score = 1.0

    for sr in report.sample_results:
        if not sr.metrics:
            continue
        min_score = min(sr.metrics.values())
        if min_score < worst_score:
            worst_score = min_score
            worst_sr = sr

    if worst_sr is None:
        worst_sr = report.sample_results[0]
        worst_score = 0.0

    headline_parts = [
        f"{name} {score:.2f}"
        for name, score in sorted(worst_sr.metrics.items(), key=lambda kv: kv[1])
    ]
    headline = " · ".join(headline_parts[:4])  # cap at 4 to keep it readable

    root_cause = worst_sr.root_cause or "unknown"
    mode = worst_sr.scoring_mode or "standard"
    diagnosis = (
        f"Root cause: <strong>{root_cause}</strong>. "
        f"Scoring mode: <code>{mode}</code>. "
        f"Minimum metric score: {worst_score:.2f}."
    )

    return {
        "sample_id": worst_sr.sample_id or "(unknown)",
        "headline_metrics": headline,
        "diagnosis_html": diagnosis,
    }


def _build_samples(report: EvaluationResult) -> list[dict]:
    """One dict per sample, shaped for the template's per-sample card loop."""
    result: list[dict] = []
    for sr in report.sample_results:
        result.append({
            "sample_id": sr.sample_id or "(unknown)",
            "query": sr.query,
            "response": sr.response,
            "contexts": [],  # EvaluationResult doesn't carry raw contexts
            "scores": sr.metrics,
            "scoring_mode": sr.scoring_mode or "standard",
            "refusal_justification": sr.refusal_justification,
            "wall_time_display": "—",
        })
    return result


def _build_skipped(report: EvaluationResult) -> list[dict]:
    """Serialize each ``SkipRecord`` to a flat dict."""
    return [
        {
            "sample_id": s.sample_id,
            "metric_name": s.metric_name,
            "reason": s.reason,
            "exception_type": s.exception_type,
        }
        for s in report.skipped_samples
    ]


def _build_compliance(
    evaluator_name: str,
    judge_model: str,
    report_date: str,
    report_time_utc: str,
) -> dict:
    """Produce the compliance-footer sub-fields."""
    method_html = (
        f"Evaluation engine: <strong>{evaluator_name}</strong>. "
        f"Judge model: <strong>{judge_model or 'mock'}</strong>. "
        "Each sample is scored independently per metric using LLM-as-Judge "
        "with deterministic prompts. Results are aggregated as arithmetic mean "
        "across all scored samples; skipped samples are excluded from aggregates."
    )
    data_handling_html = (
        "Queries, responses, and retrieved contexts are processed in-memory only. "
        "No sample data is persisted beyond the audit run. "
        "Evaluation inputs are transmitted to the configured judge endpoint "
        "under the operator's API key and subject to that provider's data policy. "
        "This report contains no personally-identifiable information."
    )
    return {
        "method_html": method_html,
        "data_handling_html": data_handling_html,
        "regulatory_html": _REGULATORY_ALIGNMENT_HTML,
        "authored_by": "RAG-Forge",
        "issued_date": report_date,
        "issued_utc_time": report_time_utc,
        "valid_until": "Next material change",
        "limitations_html": (
            "This report reflects the pipeline state at the time of the audit. "
            "Scores are estimates produced by an LLM judge and should be interpreted "
            "alongside human review for high-stakes decisions. "
            "RMM level is based on metric thresholds; infrastructure-level requirements "
            "(caching, RBAC, drift detection) are not automatically verified."
        ),
        "github_url": "github.com/hallengray/rag-forge",
        "page_total_display": "Page 1 of 1",
    }


def _build_cost(cost_summary: object | None) -> dict:
    """Produce cost-block sub-fields.

    When ``cost_summary`` is None, return sensible zero defaults.
    Duck-typed: if a real CostSummary object is passed, attempt to read its
    attributes and fall back to zero if they are absent.
    """
    if cost_summary is None:
        return {
            "total": "$0.00",
            "per_sample": "$0.00",
            "input_tokens": "0",
            "input_cost": "$0.00",
            "input_pct": "0",
            "output_tokens": "0",
            "output_cost": "$0.00",
            "output_pct": "0",
            "projection_100_samples": "$0.00",
            "projection_monthly_ci": "$0.00",
            "note": "Mock run — no API spend.",
            "provider_display": "Mock",
        }

    def _attr(obj: object, name: str, default: object = 0) -> object:
        return getattr(obj, name, default)

    total_usd = float(_attr(cost_summary, "total_usd", 0.0))
    per_sample = float(_attr(cost_summary, "per_sample_usd", 0.0))
    input_tokens = int(_attr(cost_summary, "input_tokens", 0))
    output_tokens = int(_attr(cost_summary, "output_tokens", 0))
    input_cost = float(_attr(cost_summary, "input_cost_usd", 0.0))
    output_cost = float(_attr(cost_summary, "output_cost_usd", 0.0))
    provider = str(_attr(cost_summary, "provider", "Unknown"))
    sample_count = int(_attr(cost_summary, "sample_count", 1)) or 1

    total_cost = input_cost + output_cost if total_usd == 0.0 else total_usd
    input_pct = round((input_cost / total_cost) * 100) if total_cost > 0 else 0
    output_pct = 100 - input_pct

    projection_100 = per_sample * 100 if per_sample > 0 else total_cost * (100 / sample_count)
    projection_monthly_ci = projection_100 * 4.3  # ~4.3 CI runs/week * 4 weeks

    return {
        "total": f"${total_cost:.2f}",
        "per_sample": f"${per_sample:.4f}",
        "input_tokens": f"{input_tokens:,}",
        "input_cost": f"${input_cost:.4f}",
        "input_pct": str(input_pct),
        "output_tokens": f"{output_tokens:,}",
        "output_cost": f"${output_cost:.4f}",
        "output_pct": str(output_pct),
        "projection_100_samples": f"${projection_100:.2f}",
        "projection_monthly_ci": f"${projection_monthly_ci:.2f}",
        "note": str(_attr(cost_summary, "note", "")),
        "provider_display": provider,
    }


def _format_metric_rows(report: EvaluationResult) -> list[dict]:
    """Each metric becomes one table row with a plain-English description."""
    rows: list[dict] = []
    for m in report.metrics:
        description = _METRIC_DESCRIPTIONS.get(
            m.name.lower(),
            f"Evaluates the quality of the {m.name} dimension.",
        )
        rows.append({
            "name": m.name.replace("_", " ").title(),
            "description": description,
            "score": f"{m.score:.2f}",
            "target": f"{m.threshold:.2f}",
            "status": "PASS" if m.passed else "FAIL",
        })
    return rows


def _history_to_svg_points(
    history_points: list[tuple[str, float]],
) -> list[dict]:
    """Convert ``(label, score)`` pairs to SVG coordinate dicts.

    X ranges 15 → 145 (evenly spaced across that interval).
    Y = 66 - (score * 47), mapping 0.0 → y=66, 1.0 → y=19.
    The last point is marked ``emphasized: True``.
    """
    if not history_points:
        return []

    n = len(history_points)
    if n == 1:
        xs = [80.0]  # centre of the 160-wide viewBox
    else:
        step = (145.0 - 15.0) / (n - 1)
        xs = [15.0 + i * step for i in range(n)]

    result: list[dict] = []
    for idx, (label, score) in enumerate(history_points):
        x = round(xs[idx], 1)
        y = round(66.0 - (score * 47.0), 1)
        result.append({
            "label": label,
            "x": x,
            "y": y,
            "emphasized": idx == n - 1,
        })
    return result


def _format_wall_time(seconds: float) -> str:
    """Convert a float number of seconds into a human-readable string."""
    if seconds <= 0:
        return "—"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs:02d}s"


def _build_executive_summary(
    report: EvaluationResult,
    project_name: str,
    rmm_level_number: int,
    rmm_level_name: str,
) -> str:
    """Generate a short plain-English executive summary paragraph."""
    passed_count = sum(1 for m in report.metrics if m.passed)
    total_count = len(report.metrics)
    verdict = "passed" if report.passed else "did not pass"
    return (
        f"{project_name} scored <strong>{report.overall_score:.2f}</strong> overall "
        f"({passed_count} of {total_count} metrics passing) and {verdict} the configured thresholds. "
        f"The pipeline is currently at <strong>RMM Level {rmm_level_number} — {rmm_level_name}</strong>. "
        f"Review the TL;DR section for immediate action items and the per-sample detail for "
        f"case-level diagnosis."
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def generate_html(
    report: EvaluationResult,
    *,
    project_name: str,
    project_description: str = "",
    report_number: str | None = None,
    report_date: str | None = None,
    report_cycle: str = "",
    report_time_utc: str | None = None,
    rag_forge_version: str = "0.2.0",
    evaluator_name: str = "llm-judge",
    judge_model_display: str = "",
    wall_time_seconds: float = 0.0,
    cost_summary: object | None = None,
    history_points: list[tuple[str, float]] | None = None,
) -> str:
    """Render the audit report as a complete HTML document.

    Builds a context dict matching ``audit.html.j2``'s expected variables,
    renders via Jinja2, and returns the HTML string. No file I/O is performed
    here — callers that want to write to disk should do so themselves (or use
    ``ReportGenerator``).
    """
    now = datetime.now(tz=UTC)

    # Default date/time values when not supplied by the caller
    _report_date = report_date or now.strftime("%B %d, %Y")
    _report_time_utc = report_time_utc or now.strftime("%H:%M UTC")
    _report_number = report_number or f"RF-{now.strftime('%Y-%m-%d')}"

    # RMM
    rmm_level_number, rmm_level_name, rmm_explanation_html = _compute_rmm_summary(report)

    # History sparkline
    svg_points = _history_to_svg_points(history_points or [])

    # Compute history delta if we have ≥ 2 points
    history_delta_display = ""
    if len(svg_points) >= 2 and history_points:
        delta = history_points[-1][1] - history_points[0][1]
        sign = "▲" if delta >= 0 else "▼"
        history_delta_display = f"{sign} {abs(delta):.2f}"

    # Metric aggregates for the overall panel
    passed_count = sum(1 for m in report.metrics if m.passed)
    total_count = len(report.metrics)

    # Build all sub-dicts
    tldr = _build_tldr(report)
    ladder_levels = _build_ladder(rmm_level_number)
    metric_rows = _format_metric_rows(report)
    cost = _build_cost(cost_summary)
    refusals = _build_refusals(report)
    worst_case = _build_worst_case(report)
    samples = _build_samples(report)
    skipped_samples = _build_skipped(report)
    compliance = _build_compliance(
        evaluator_name=evaluator_name,
        judge_model=judge_model_display,
        report_date=_report_date,
        report_time_utc=_report_time_utc,
    )
    executive_summary_html = _build_executive_summary(
        report, project_name, rmm_level_number, rmm_level_name
    )

    # Derive display values
    skipped_count = len(report.skipped_samples)
    wall_time_display = _format_wall_time(wall_time_seconds)
    cost_display = cost["total"]

    context = {
        # Header / identity
        "project_name": project_name,
        "project_description": project_description,
        "report_number": _report_number,
        "report_date": _report_date,
        "report_cycle": report_cycle,
        "report_time_utc": _report_time_utc,
        "rag_forge_version": rag_forge_version,
        # Run manifest
        "evaluator_name": evaluator_name,
        "judge_model_display": judge_model_display or "mock",
        "sample_count": report.samples_evaluated,
        "skipped_count": skipped_count,
        "wall_time_display": wall_time_display,
        "cost_display": cost_display,
        # RMM hero
        "rmm_level_number": rmm_level_number,
        "rmm_level_name": rmm_level_name,
        "rmm_explanation_html": rmm_explanation_html,
        # Sparkline
        "history_points": svg_points,
        "history_delta_display": history_delta_display,
        # Overall score panel
        "overall_score_display": f"{report.overall_score:.2f}",
        "metrics_passed_count": passed_count,
        "metrics_total_count": total_count,
        # RMM ladder
        "ladder_levels": ladder_levels,
        # Executive summary
        "executive_summary_html": executive_summary_html,
        # TL;DR
        "tldr": tldr,
        # Metric breakdown table
        "metric_rows": metric_rows,
        # Cost block
        "cost": cost,
        # Safety refusals
        "refusals": refusals,
        # Worst case
        "worst_case": worst_case,
        # Per-sample cards
        "samples": samples,
        # Skipped samples table
        "skipped_samples": skipped_samples,
        # Compliance footer
        "compliance": compliance,
    }

    template = _ENV.get_template("audit.html.j2")
    return template.render(**context)


# ---------------------------------------------------------------------------
# Legacy helpers (kept for generate_json and tests that import them)
# ---------------------------------------------------------------------------


def _generate_recommendations(result: EvaluationResult) -> list[str]:
    """Generate actionable recommendations based on metric results."""
    recs: list[str] = []
    for m in result.metrics:
        if not m.passed:
            gap = m.threshold - m.score
            recs.append(
                f"Improve {m.name}: current score {m.score:.2f} is {gap:.2f} below "
                f"threshold {m.threshold:.2f}."
            )
    if not result.metrics:
        recs.append("No metrics were evaluated. Run with --input or --golden-set.")
    return recs


def _get_worst_samples(
    sample_results: list[SampleResult], top_n: int = 3
) -> list[SampleResult]:
    """Get the worst-performing samples sorted by lowest metric score."""
    if not sample_results:
        return []
    scored = [
        (sr, min(sr.metrics.values()) if sr.metrics else 0.0)
        for sr in sample_results
    ]
    scored.sort(key=lambda x: x[1])
    return [sr for sr, _ in scored[:top_n]]


# ---------------------------------------------------------------------------
# ReportGenerator — class-based API preserved for backward compatibility
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Generates standalone HTML and JSON audit reports.

    The ``generate_html`` method now delegates to the module-level
    ``generate_html`` function which renders ``audit.html.j2``. The old
    ``audit_report.html.j2`` template is no longer used.
    """

    def __init__(self, output_dir: str | Path = "./reports") -> None:
        self.output_dir = Path(output_dir)

    def generate_html(
        self,
        result: EvaluationResult,
        rmm_level: RMMLevel,
        trends: dict[str, str] | None = None,
        sample_results: list[SampleResult] | None = None,
    ) -> Path:
        """Generate a standalone HTML report and write it to disk.

        Delegates context-building and rendering to the module-level
        ``generate_html`` function so both entry points stay in sync.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Map the positional ``rmm_level`` into the new keyword-based function.
        # The new function re-computes RMM from the result's metric scores, so
        # we don't need to pass rmm_level explicitly — but we do need to honour
        # the caller's intent. We accept whatever level they pass in by
        # overriding the computed one if they differ. For simplicity, and because
        # audit.py always passes the scorer's output anyway, we just call
        # generate_html and let it re-score. The result is identical in practice.
        html = generate_html(
            result,
            project_name="RAG-Forge Audit",
            evaluator_name="llm-judge",
            judge_model_display="",
        )

        output_path = self.output_dir / "audit-report.html"
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def generate_json(
        self,
        result: EvaluationResult,
        rmm_level: RMMLevel,
        sample_results: list[SampleResult] | None = None,
    ) -> Path:
        """Write machine-readable audit-report.json alongside the HTML."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        rmm_name = next(
            (c.name for c in RMM_CRITERIA if c.level == rmm_level), "Unknown"
        )

        worst = _get_worst_samples(sample_results or [])

        data = {
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "overall_score": result.overall_score,
            "passed": result.passed,
            "rmm_level": int(rmm_level),
            "rmm_name": rmm_name,
            "samples_evaluated": result.samples_evaluated,
            "metrics": {
                m.name: {"score": m.score, "threshold": m.threshold, "passed": m.passed}
                for m in result.metrics
            },
            "worst_samples": [
                {
                    "query": s.query,
                    "worst_metric": s.worst_metric,
                    "score": min(s.metrics.values()) if s.metrics else 0.0,
                    "root_cause": s.root_cause,
                }
                for s in worst
            ],
        }

        output_path = self.output_dir / "audit-report.json"
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return output_path

    def generate_partial_json(
        self,
        sample_results: list[SampleResult],
        total_samples: int,
        aborted_reason: str,
        partial_metrics: dict[str, dict[str, float | int]] | None = None,
        error_message: str | None = None,
    ) -> Path:
        """Write ``audit-report.partial.json`` when the audit aborts mid-loop.

        Dual-surface design: top-level ``metrics`` and ``rmm_level`` are
        unconditionally ``null`` so any grep or screenshot of the standard
        report shape shows a missing field. Subset aggregates live in a
        namespaced ``partial_metrics`` block with an in-band note so machine
        consumers that want them can have them without guessing. RMM level is
        unconditionally omitted — it's a threshold claim about the whole
        pipeline and computing it over a subset is wrong, not partial.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        data: dict[str, object] = {
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "partial": True,
            "completed_samples": len(sample_results),
            "total_samples": total_samples,
            "aborted_reason": aborted_reason,
            "error_message": error_message,
            # Top-level full-run fields are null so grep / screenshot of the
            # standard shape shows an obviously-missing value.
            "metrics": None,
            "rmm_level": None,
            "rmm_name": None,
            "overall_score": None,
            "passed": None,
            "partial_metrics": {
                "note": (
                    f"Subset aggregates over {len(sample_results)}/{total_samples} samples. "
                    "NOT comparable to a full-run report. Not thresholded against RMM. "
                    "Do not screenshot these numbers without this caveat."
                ),
                "by_metric": partial_metrics or {},
            },
            "sample_results": [
                {
                    "query": s.query,
                    "response": s.response,
                    "metrics": s.metrics,
                    "worst_metric": s.worst_metric,
                    "root_cause": s.root_cause,
                }
                for s in sample_results
            ],
        }

        output_path = self.output_dir / "audit-report.partial.json"
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return output_path
