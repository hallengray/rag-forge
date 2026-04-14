"""Visual regression test for the audit report.

Gated by @pytest.mark.visual — skipped by default. Run with:
    uv run pytest -m visual packages/evaluator/tests/test_report_visual_regression.py

First-time setup: the test writes a baseline PNG to
tests/fixtures/visual_baseline/audit_report_baseline.png on first run
(and skips with a message asking you to commit it). Re-run after
committing to exercise the actual pixel-diff comparison.

The baseline is OS-dependent (font rendering, anti-aliasing), so this
test is most useful on a pinned CI runner. Locally, expect up to 0.5%
pixel drift to be tolerated.
"""

from pathlib import Path

import pytest

# Module-level importorskip — if playwright or pillow are missing, the
# whole module is skipped cleanly without contributing failures.
playwright = pytest.importorskip("playwright.sync_api")
PIL = pytest.importorskip("PIL")


BASELINE_DIR = Path(__file__).parent / "fixtures" / "visual_baseline"
BASELINE_PATH = BASELINE_DIR / "audit_report_baseline.png"


def _make_deterministic_report():
    """Build the same EvaluationResult the test_report_generator tests use
    so we can reuse the shape without re-defining it here."""
    from rag_forge_evaluator.engine import (
        EvaluationResult,
        MetricResult,
        SampleResult,
    )

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
                response="Immediate IV labetalol titration per protocol.",
                metrics={"faithfulness": 0.54, "answer_relevance": 0.93, "context_relevance": 0.62, "hallucination": 0.55},
                worst_metric="faithfulness",
                root_cause="generation drift",
                sample_id="htn-001-emergency-end-organ",
                scoring_mode="standard",
                refusal_justification=None,
            ),
            SampleResult(
                query="What dose of metformin for my 11 year old?",
                response="I cannot provide paediatric dosing without clinical supervision.",
                metrics={"faithfulness": 1.0, "answer_relevance": 0.9, "context_relevance": 0.7, "hallucination": 1.0},
                worst_metric="context_relevance",
                root_cause="none",
                sample_id="t2dm-002-paediatric-dosing-refusal",
                scoring_mode="safety_refusal",
                refusal_justification="Context lacks paediatric dosing; response correctly declined",
            ),
        ],
        scoring_modes_count={"standard": 11, "safety_refusal": 1},
    )


@pytest.mark.visual
def test_audit_report_visual_matches_baseline(tmp_path):
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageChops
    from rag_forge_evaluator.report.generator import generate_html

    report = _make_deterministic_report()
    html = generate_html(
        report,
        project_name="VisualFixture",
        report_date="April 14, 2026",
        report_time_utc="13:16 UTC",
        report_number="RF-TEST-0001",
        evaluator_name="llm-judge",
        judge_model_display="claude-sonnet-4-6",
        wall_time_seconds=516,
    )

    output = tmp_path / "rendered.png"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=str(output), full_page=True)
        browser.close()

    if not BASELINE_PATH.exists():
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_bytes(output.read_bytes())
        pytest.skip(
            f"Baseline captured at {BASELINE_PATH}. Commit it and re-run the test "
            f"to exercise the pixel-diff comparison."
        )

    baseline_img = Image.open(BASELINE_PATH).convert("RGB")
    actual_img = Image.open(output).convert("RGB")

    # Resize baseline if dimensions drifted (defensive)
    if baseline_img.size != actual_img.size:
        pytest.fail(
            f"Image size mismatch: baseline {baseline_img.size} vs actual {actual_img.size}. "
            f"Re-capture the baseline if the template deliberately changed layout."
        )

    diff = ImageChops.difference(baseline_img, actual_img)
    bbox = diff.getbbox()
    if bbox is None:
        return  # byte-identical

    total_pixels = baseline_img.width * baseline_img.height
    diff_pixels = sum(1 for p in diff.getdata() if p != (0, 0, 0))
    diff_ratio = diff_pixels / total_pixels
    assert diff_ratio < 0.005, (
        f"{diff_pixels}/{total_pixels} pixels differ from baseline ({diff_ratio:.2%}). "
        f"Re-capture baseline if the template deliberately changed."
    )
