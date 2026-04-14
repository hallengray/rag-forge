"""Smoke test: the audit.html.j2 template loads and renders with a
minimal context without raising TemplateNotFound or UndefinedError."""

from jinja2 import Environment, PackageLoader, StrictUndefined


def _minimal_context() -> dict:
    return {
        "project_name": "TestProject",
        "project_description": "A test project",
        "report_number": "RF-TEST-001",
        "report_date": "April 14, 2026",
        "report_cycle": "Cycle 1",
        "report_time_utc": "13:16 UTC",
        "rag_forge_version": "0.2.0",
        "evaluator_name": "llm-judge",
        "judge_model_display": "mock-judge",
        "sample_count": 2,
        "skipped_count": 0,
        "wall_time_display": "1m 23s",
        "cost_display": "$0.00",
        "rmm_level_number": 1,
        "rmm_level_name": "Better Recall",
        "rmm_explanation_html": "Test explanation.",
        "overall_score_display": "0.74",
        "metrics_passed_count": 1,
        "metrics_total_count": 4,
        "history_points": [
            {"label": "C1", "x": 15, "y": 66},
            {"label": "C2", "x": 145, "y": 19},
        ],
        "history_delta_display": "+0.46",
        "ladder_levels": [
            {"number": 0, "name": "Naive", "state": "cleared"},
            {"number": 1, "name": "Better Recall", "state": "current"},
            {"number": 2, "name": "Better Precision", "state": "next"},
            {"number": 3, "name": "Better Trust", "state": "future"},
            {"number": 4, "name": "Better Workflow", "state": "future"},
            {"number": 5, "name": "Enterprise", "state": "future"},
        ],
        "executive_summary_html": "Test summary.",
        "tldr": {
            "working": ["Answer relevance passed"],
            "needs_fixing": ["Faithfulness 0.78 / 0.85"],
            "priority_next_step_html": "Investigate htn-001 drift.",
        },
        "metric_rows": [
            {
                "name": "Faithfulness",
                "description": "Does the answer stay true to the sources?",
                "score": "0.78",
                "target": "0.85",
                "status": "FAIL",
            },
            {
                "name": "Answer Relevance",
                "description": "Does the answer address the question?",
                "score": "0.87",
                "target": "0.80",
                "status": "PASS",
            },
        ],
        "cost": {
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
            "note": "Mock run, no API spend.",
            "provider_display": "Mock",
        },
        "refusals": {
            "count": 0,
            "total": 2,
            "rate_percent": "0",
            "warn": False,
            "warning_text": "",
            "cases": [],
        },
        "worst_case": {
            "sample_id": "test-001",
            "headline_metrics": "faithfulness 0.78",
            "diagnosis_html": "Drift observed.",
        },
        "samples": [
            {
                "sample_id": "test-001",
                "query": "Q",
                "response": "R",
                "contexts": ["C"],
                "scores": {"faithfulness": 0.78},
                "scoring_mode": "standard",
                "refusal_justification": None,
                "wall_time_display": "2.1s",
            }
        ],
        "skipped_samples": [],
        "compliance": {
            "method_html": "Method.",
            "data_handling_html": "Data handling.",
            "regulatory_html": (
                "This audit aligns with <strong>NIST AI Risk Management Framework (AI RMF 1.0)</strong> "
                "§ 4.3 Measure · <strong>ISO/IEC 42001:2023</strong> AI Management System § 8.3 · "
                "<strong>EU AI Act Article 15</strong> accuracy, robustness and cybersecurity testing."
            ),
            "authored_by": "RAG-Forge",
            "issued_date": "April 14, 2026",
            "issued_utc_time": "13:16:45 UTC",
            "valid_until": "Next material change",
            "limitations_html": "Limitations.",
            "github_url": "github.com/hallengray/rag-forge",
            "page_total_display": "Page 1 of 14",
        },
    }


def test_template_loads_and_renders_with_minimal_context() -> None:
    env = Environment(
        loader=PackageLoader("rag_forge_evaluator", "report/templates"),
        undefined=StrictUndefined,  # catches every missing key
        autoescape=True,
    )
    template = env.get_template("audit.html.j2")
    html = template.render(**_minimal_context())

    assert "<!DOCTYPE html>" in html
    assert "TestProject" in html
    assert "Better Recall" in html
    assert (
        "TL;DR" in html.upper()
        or "tl;dr" in html.lower()
        or "Priority next step" in html
    )
    assert "RAG-Forge" in html
    # Sparkline rendered
    assert "<svg" in html
    # Compliance footer references regulatory frameworks
    assert "NIST" in html or "ISO/IEC 42001" in html or "EU AI Act" in html
    # No fingerprint (removed per design decision)
    assert "SHA-256" not in html


def test_template_renders_empty_skipped_samples_block_hidden() -> None:
    """When skipped_samples is empty, the skipped section should NOT appear."""
    env = Environment(
        loader=PackageLoader("rag_forge_evaluator", "report/templates"),
        undefined=StrictUndefined,
        autoescape=True,
    )
    template = env.get_template("audit.html.j2")
    html = template.render(**_minimal_context())

    assert "These samples could not be scored" not in html


def test_template_renders_skipped_samples_block_when_present() -> None:
    env = Environment(
        loader=PackageLoader("rag_forge_evaluator", "report/templates"),
        undefined=StrictUndefined,
        autoescape=True,
    )
    template = env.get_template("audit.html.j2")
    ctx = _minimal_context()
    ctx["skipped_samples"] = [
        {
            "sample_id": "s2",
            "metric_name": "faithfulness",
            "reason": "timeout",
            "exception_type": "TimeoutError",
        }
    ]
    html = template.render(**ctx)

    assert "These samples could not be scored" in html
    assert "s2" in html
    assert "TimeoutError" in html
