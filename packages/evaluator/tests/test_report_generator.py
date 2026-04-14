"""Tests for the new audit report generator (context builder + render)."""

from rag_forge_evaluator.engine import (
    EvaluationResult,
    MetricResult,
    SampleResult,
    SkipRecord,
)
from rag_forge_evaluator.report.generator import generate_html


def _make_report() -> EvaluationResult:
    return EvaluationResult(
        metrics=[
            MetricResult(name="faithfulness", score=0.78, threshold=0.85, passed=False),
            MetricResult(name="answer_relevance", score=0.87, threshold=0.80, passed=True),
            MetricResult(name="context_relevance", score=0.60, threshold=0.80, passed=False),
            MetricResult(name="hallucination", score=0.71, threshold=0.95, passed=False),
        ],
        overall_score=0.74,
        samples_evaluated=12,
        passed=False,
        sample_results=[
            SampleResult(
                query="How do I manage hypertensive emergency?",
                response="Give diazepam…",
                metrics={"faithfulness": 0.54, "answer_relevance": 0.93, "context_relevance": 0.62, "hallucination": 0.55},
                worst_metric="faithfulness",
                root_cause="generation drift",
                sample_id="htn-001-emergency-end-organ",
                scoring_mode="standard",
                refusal_justification=None,
            ),
            SampleResult(
                query="What dose of metformin for my 11 year old?",
                response="I cannot provide paediatric dosing without supervision.",
                metrics={"faithfulness": 1.0, "answer_relevance": 0.9, "context_relevance": 0.7, "hallucination": 1.0},
                worst_metric="context_relevance",
                root_cause="none",
                sample_id="t2dm-002-paediatric-dosing-refusal",
                scoring_mode="safety_refusal",
                refusal_justification="Context lacks paediatric dosing; response correctly declined",
            ),
        ],
        skipped_samples=[],
        scoring_modes_count={"standard": 11, "safety_refusal": 1},
    )


def test_generate_html_contains_project_name():
    html = generate_html(_make_report(), project_name="PearMedica")
    assert "PearMedica" in html


def test_generate_html_contains_rmm_level_and_explanation():
    html = generate_html(_make_report(), project_name="PearMedica")
    # Some kind of RMM level must appear
    assert "Level" in html
    # Plain-English phrase about advancing to the next level
    assert "Level" in html and ("Better Recall" in html or "Better Precision" in html or "Naive" in html)


def test_generate_html_shows_tldr_sections():
    html = generate_html(_make_report(), project_name="PearMedica")
    assert "What's working" in html
    assert "What needs fixing" in html
    assert "Priority next step" in html.lower() or "priority next step" in html.lower() or "Priority next step" in html


def test_generate_html_shows_safety_refusal_case():
    html = generate_html(_make_report(), project_name="PearMedica")
    # The safety-refusal sample id should appear in the refusals section
    assert "t2dm-002" in html
    # And the justification quoted
    assert "paediatric" in html


def test_generate_html_renders_compliance_footer_with_rag_forge_author():
    html = generate_html(_make_report(), project_name="PearMedica")
    assert "RAG-Forge" in html
    assert "NIST" in html
    assert "ISO/IEC 42001" in html
    # No fingerprint (removed from design)
    assert "SHA-256" not in html


def test_generate_html_shows_refusal_rate():
    html = generate_html(_make_report(), project_name="PearMedica")
    # 1 refusal / 12 samples ≈ 8%
    assert "8" in html


def test_generate_html_omits_refusal_warning_when_rate_low():
    html = generate_html(_make_report(), project_name="PearMedica")
    assert "High refusal rate detected" not in html


def test_generate_html_shows_refusal_warning_when_rate_high():
    """Build a report where 5 of 12 samples are refusals (~42%) — above 30% threshold."""
    report = _make_report()
    # Replace sample_results with 7 standard + 5 safety_refusal
    report.sample_results = [
        SampleResult(
            query=f"q{i}", response="r", metrics={"faithfulness": 0.9},
            worst_metric="faithfulness", root_cause="none",
            sample_id=f"s{i}", scoring_mode="standard",
        )
        for i in range(7)
    ] + [
        SampleResult(
            query=f"q{i}", response="I cannot", metrics={"faithfulness": 1.0},
            worst_metric="context_relevance", root_cause="none",
            sample_id=f"refusal-{i}", scoring_mode="safety_refusal",
            refusal_justification="Context lacks info",
        )
        for i in range(5)
    ]
    report.samples_evaluated = 12
    report.scoring_modes_count = {"standard": 7, "safety_refusal": 5}

    html = generate_html(report, project_name="PearMedica")
    assert "High refusal rate detected" in html


def test_generate_html_shows_skipped_section_when_skips_present():
    report = _make_report()
    report.skipped_samples = [
        SkipRecord(sample_id="s-broken", metric_name="faithfulness", reason="timeout", exception_type="TimeoutError"),
    ]
    html = generate_html(report, project_name="PearMedica")
    assert "s-broken" in html
    assert "TimeoutError" in html


def test_generate_html_plain_english_metric_descriptions():
    html = generate_html(_make_report(), project_name="PearMedica")
    # The "What it measures" column has plain-English phrasing
    assert "stay true to the retrieved sources" in html or "stay true" in html
    assert "address what was asked" in html or "address the question" in html.lower()
