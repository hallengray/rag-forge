"""Aggregation must exclude skipped samples (Bug #8 fix)."""
from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator


class _ScriptedJudge:
    """Returns scripted responses in order. Empty string = simulate parse failure."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        _ = system_prompt, user_prompt
        return self._responses.pop(0)

    def model_name(self) -> str:
        return "scripted"


def _sample(query: str) -> EvaluationSample:
    return EvaluationSample(
        query=query,
        response="a response",
        contexts=["some context"],
        expected_answer=None,
    )


def _good(metric_field: str, value: float) -> str:
    return '{"' + metric_field + '": ' + str(value) + "}"


def test_aggregate_excludes_skipped_samples_from_mean() -> None:
    """Two samples; second sample's metrics all parse-fail. Mean should be over sample 1 only."""
    # LLMJudgeEvaluator default metric order:
    # FaithfulnessMetric, ContextRelevanceMetric, AnswerRelevanceMetric, HallucinationMetric
    # Sample 1: all four succeed with high scores.
    # Sample 2: all four return empty string (parse fail).
    responses = [
        _good("score", 0.9),               # sample1 faithfulness
        _good("mean_score", 0.9),          # sample1 context_relevance
        _good("overall_score", 0.9),       # sample1 answer_relevance
        _good("hallucination_rate", 0.1),  # sample1 hallucination → score 0.9
        "",                                 # sample2 faithfulness FAIL
        "",                                 # sample2 context_relevance FAIL
        "",                                 # sample2 answer_relevance FAIL
        "",                                 # sample2 hallucination FAIL
    ]
    judge = _ScriptedJudge(responses)
    evaluator = LLMJudgeEvaluator(judge=judge)
    result = evaluator.evaluate([_sample("q1"), _sample("q2")])

    by_name = {m.name: m for m in result.metrics}
    # Real avg over the 1 successful sample is 0.9, NOT (0.9 + 0)/2 = 0.45.
    for name in ("faithfulness", "context_relevance", "answer_relevance", "hallucination"):
        assert by_name[name].score >= 0.85, (
            f"{name}: expected ~0.9 (skipping the failed sample), got {by_name[name].score}"
        )
        assert by_name[name].scored_count == 1
        assert by_name[name].skipped_count == 1
    assert result.skipped_evaluations == 4


def test_aggregate_passes_when_all_real_scores_above_threshold() -> None:
    """Even with skips, a metric should pass if its scored samples meet threshold."""
    responses = [
        _good("score", 0.9),
        _good("mean_score", 0.9),
        _good("overall_score", 0.9),
        _good("hallucination_rate", 0.0),
        "",
        "",
        "",
        "",
    ]
    judge = _ScriptedJudge(responses)
    evaluator = LLMJudgeEvaluator(judge=judge)
    result = evaluator.evaluate([_sample("q1"), _sample("q2")])

    by_name = {m.name: m for m in result.metrics}
    assert by_name["faithfulness"].passed is True
    assert by_name["answer_relevance"].passed is True
    assert by_name["hallucination"].passed is True


def test_aggregate_marks_metric_failed_when_no_scored_samples() -> None:
    """If every sample for a metric is skipped, the metric must report passed=False."""
    responses = [""] * 8  # 2 samples * 4 metrics, all parse-fail
    judge = _ScriptedJudge(responses)
    evaluator = LLMJudgeEvaluator(judge=judge)
    result = evaluator.evaluate([_sample("q1"), _sample("q2")])

    for m in result.metrics:
        assert m.passed is False
        assert m.scored_count == 0
        assert m.skipped_count == 2


def test_missing_field_is_skipped_not_zero() -> None:
    """Per PearMedica forensic finding: when judge JSON parses but the expected
    field is absent, the metric must be skipped — not treated as worst-case.
    """
    # Valid JSON but missing the expected score keys.
    bad_responses = [
        '{"reason": "I cannot evaluate this"}',  # faithfulness missing 'score'
        '{"reason": "no context provided"}',     # context_relevance missing 'mean_score'
        '{"reason": "tangential"}',              # answer_relevance missing 'overall_score'
        '{"reason": "cannot determine"}',        # hallucination missing 'hallucination_rate'
    ]
    judge = _ScriptedJudge(bad_responses)
    evaluator = LLMJudgeEvaluator(judge=judge)
    result = evaluator.evaluate([_sample("q1")])

    for m in result.metrics:
        assert m.scored_count == 0
        assert m.skipped_count == 1
    assert result.skipped_evaluations == 4


def test_pearmedica_pollution_scenario() -> None:
    """Reproduce the exact pathology from the 2026-04-13 audit at smaller scale.

    19 samples with 27/76 parse failures dragged context_relevance to 0.063
    when the real mean over the 4 scored samples was ~0.30. Verify the new
    aggregation reports the real mean instead of the polluted one.
    """
    # Build 4 samples. For context_relevance only, 3 parse-fail and 1 succeeds with mean_score=0.30.
    # For other metrics, all 4 succeed with high scores.
    responses: list[str] = []
    for i in range(4):
        responses.append(_good("score", 0.9))                # faithfulness
        if i == 0:
            responses.append(_good("mean_score", 0.30))       # context_relevance succeeds
        else:
            responses.append("")                              # context_relevance fails
        responses.append(_good("overall_score", 0.9))        # answer_relevance
        responses.append(_good("hallucination_rate", 0.05))  # hallucination

    judge = _ScriptedJudge(responses)
    evaluator = LLMJudgeEvaluator(judge=judge)
    result = evaluator.evaluate([_sample(f"q{i}") for i in range(4)])

    by_name = {m.name: m for m in result.metrics}
    # Old behavior would have reported context_relevance = (0.30 + 0 + 0 + 0) / 4 = 0.075
    # New behavior reports the real mean over the 1 scored sample: 0.30
    assert by_name["context_relevance"].score == 0.30
    assert by_name["context_relevance"].scored_count == 1
    assert by_name["context_relevance"].skipped_count == 3
