"""Tests for engine type definitions."""

from rag_forge_evaluator.engine import (
    EvaluationResult,
    MetricResult,
    SampleResult,
    SkipRecord,
)


def test_skip_record_is_a_dataclass_with_required_fields():
    record = SkipRecord(
        sample_id="case-001",
        metric_name="faithfulness",
        reason="ragas InstructorRetryException",
        exception_type="InstructorRetryException",
    )
    assert record.sample_id == "case-001"
    assert record.metric_name == "faithfulness"


def test_metric_result_accepts_scoring_mode_and_justification():
    result = MetricResult(
        name="faithfulness",
        score=1.0,
        threshold=0.85,
        passed=True,
        scoring_mode="safety_refusal",
        refusal_justification="Pure refusal — no unsupported claims",
    )
    assert result.scoring_mode == "safety_refusal"
    assert result.refusal_justification.startswith("Pure")


def test_evaluation_result_defaults_skipped_and_modes_empty():
    evaluation = EvaluationResult(
        metrics=[],
        overall_score=0.0,
        samples_evaluated=0,
        passed=False,
    )
    assert evaluation.skipped_samples == []
    assert evaluation.scoring_modes_count == {}


def test_sample_result_accepts_scoring_mode_and_justification():
    sample = SampleResult(
        query="q",
        response="r",
        metrics={"faithfulness": 0.9},
        worst_metric="faithfulness",
        root_cause="none",
        scoring_mode="standard",
        refusal_justification=None,
    )
    assert sample.scoring_mode == "standard"
    assert sample.refusal_justification is None
