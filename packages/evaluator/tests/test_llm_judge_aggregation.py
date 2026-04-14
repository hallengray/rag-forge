"""Aggregation must exclude skipped samples (Bug #8 fix).

NOTE: These tests use the combined single-call path introduced in v0.2.0.
Each judge call returns all four metric scores in one JSON object (or an
empty string to simulate a parse failure). The old per-metric response
format ({"score": 0.9} etc.) is no longer used on the default code path.
"""
import json

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


def _good_combined(
    faithfulness: float = 0.9,
    context_relevance: float = 0.9,
    answer_relevance: float = 0.9,
    hallucination: float = 0.9,
) -> str:
    """Build a combined-format judge response with all four metrics."""
    return json.dumps({
        "faithfulness": faithfulness,
        "context_relevance": context_relevance,
        "answer_relevance": answer_relevance,
        "hallucination": hallucination,
    })


def test_aggregate_excludes_skipped_samples_from_mean() -> None:
    """Two samples; second sample parse-fails. Mean should be over sample 1 only.

    The combined path fires one judge call per sample. Sample 1 returns valid
    combined JSON; sample 2 returns an empty string (parse failure).
    """
    responses = [
        _good_combined(),  # sample1 — all four metrics succeed at 0.9
        "",                # sample2 — parse failure, all four metrics skipped
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
        _good_combined(faithfulness=0.9, context_relevance=0.9, answer_relevance=0.9, hallucination=0.96),
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
    """If every sample parse-fails, every metric must report passed=False."""
    responses = ["", ""]  # 2 samples, both parse-fail
    judge = _ScriptedJudge(responses)
    evaluator = LLMJudgeEvaluator(judge=judge)
    result = evaluator.evaluate([_sample("q1"), _sample("q2")])

    for m in result.metrics:
        assert m.passed is False
        assert m.scored_count == 0
        assert m.skipped_count == 2


def test_missing_field_is_skipped_not_zero() -> None:
    """Per cycle-1 forensic finding: when judge JSON parses but the expected
    fields are absent, every metric must be skipped — not treated as worst-case.

    The combined path treats a response with no recognised metric keys as a
    full-sample skip (all four metrics skipped).
    """
    # Valid JSON but missing all four metric keys.
    bad_response = '{"reason": "I cannot evaluate this"}'
    judge = _ScriptedJudge([bad_response])
    evaluator = LLMJudgeEvaluator(judge=judge)
    result = evaluator.evaluate([_sample("q1")])

    for m in result.metrics:
        assert m.scored_count == 0
        assert m.skipped_count == 1
    assert result.skipped_evaluations == 4


def test_cycle1_pollution_scenario() -> None:
    """Reproduce the exact pathology from the 2026-04-13 audit at smaller scale.

    19 samples with 27/76 parse failures dragged context_relevance to 0.063
    when the real mean over scored samples was ~0.30. Verify the new aggregation
    reports the real mean instead of the polluted one.

    In the combined path a parse failure drops all four metrics for that sample.
    To test per-metric skipping (only context_relevance missing), we use JSON
    that omits context_relevance on three of the four samples.
    """
    responses: list[str] = []
    for i in range(4):
        if i == 0:
            # Sample 0: all four fields present; context_relevance = 0.30
            responses.append(_good_combined(
                faithfulness=0.9,
                context_relevance=0.30,
                answer_relevance=0.9,
                hallucination=0.95,
            ))
        else:
            # Samples 1-3: context_relevance field intentionally omitted
            responses.append(json.dumps({
                "faithfulness": 0.9,
                "answer_relevance": 0.9,
                "hallucination": 0.95,
            }))

    judge = _ScriptedJudge(responses)
    evaluator = LLMJudgeEvaluator(judge=judge)
    result = evaluator.evaluate([_sample(f"q{i}") for i in range(4)])

    by_name = {m.name: m for m in result.metrics}
    # Old behavior would have reported context_relevance = (0.30 + 0 + 0 + 0) / 4 = 0.075
    # New behavior reports the real mean over the 1 scored sample: 0.30
    assert by_name["context_relevance"].score == 0.30
    assert by_name["context_relevance"].scored_count == 1
    assert by_name["context_relevance"].skipped_count == 3
