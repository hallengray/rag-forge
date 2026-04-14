"""Tests for refusal-aware scoring in the llm-judge evaluator."""

import json

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator


class StubJudge:
    """Returns canned JSON responses so we can steer classification."""

    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = payloads
        self._i = 0

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        payload = self._payloads[self._i]
        self._i += 1
        return json.dumps(payload)

    def model_name(self) -> str:
        return "stub-judge"


STANDARD_PAYLOAD = {
    "scoring_mode": "standard",
    "refusal_justification": None,
    "faithfulness": 0.9,
    "answer_relevance": 0.85,
    "context_relevance": 0.82,
    "hallucination": 0.95,
}

REFUSAL_PAYLOAD = {
    "scoring_mode": "safety_refusal",
    "refusal_justification": "Context lacks paediatric dosing; response declined to fabricate",
    "faithfulness": 1.0,
    "answer_relevance": 0.9,
    "context_relevance": 0.7,
    "hallucination": 1.0,
}


def test_standard_sample_preserves_scores():
    judge = StubJudge([STANDARD_PAYLOAD])
    evaluator = LLMJudgeEvaluator(judge=judge, thresholds={}, refusal_aware=True)

    samples = [EvaluationSample(query="q", contexts=["c"], response="r", sample_id="s1")]
    result = evaluator.evaluate(samples)

    assert result.sample_results[0].scoring_mode == "standard"
    assert result.sample_results[0].refusal_justification is None
    assert result.scoring_modes_count == {"standard": 1}


def test_safety_refusal_sample_captures_justification():
    judge = StubJudge([REFUSAL_PAYLOAD])
    evaluator = LLMJudgeEvaluator(judge=judge, thresholds={}, refusal_aware=True)

    samples = [EvaluationSample(query="q", contexts=["c"], response="r", sample_id="s1")]
    result = evaluator.evaluate(samples)

    assert result.sample_results[0].scoring_mode == "safety_refusal"
    assert "paediatric" in result.sample_results[0].refusal_justification
    assert result.scoring_modes_count == {"safety_refusal": 1}


def test_strict_mode_drops_classification_preamble():
    """When refusal_aware=False the user prompt must NOT contain the
    classification instructions. We assert this by capturing the prompts
    the judge received."""
    captured_prompts: list[str] = []

    class CapturingJudge:
        def __init__(self, payloads):
            self._payloads = payloads
            self._i = 0

        def judge(self, system_prompt: str, user_prompt: str) -> str:
            captured_prompts.append(user_prompt)
            payload = self._payloads[self._i]
            self._i += 1
            return json.dumps(payload)

        def model_name(self) -> str:
            return "capturing"

    judge = CapturingJudge([STANDARD_PAYLOAD])
    evaluator = LLMJudgeEvaluator(judge=judge, thresholds={}, refusal_aware=False)
    samples = [EvaluationSample(query="q", contexts=["c"], response="r", sample_id="s1")]
    evaluator.evaluate(samples)

    assert "safety_refusal" not in captured_prompts[0]
    assert "safety refusal" not in captured_prompts[0].lower()


def test_refusal_aware_mode_injects_preamble():
    """Inverse of the strict test: when refusal_aware=True the preamble
    IS present in the user prompt."""
    captured_prompts: list[str] = []

    class CapturingJudge:
        def __init__(self, payloads):
            self._payloads = payloads
            self._i = 0

        def judge(self, system_prompt: str, user_prompt: str) -> str:
            captured_prompts.append(user_prompt)
            payload = self._payloads[self._i]
            self._i += 1
            return json.dumps(payload)

        def model_name(self) -> str:
            return "capturing"

    judge = CapturingJudge([STANDARD_PAYLOAD])
    evaluator = LLMJudgeEvaluator(judge=judge, thresholds={}, refusal_aware=True)
    samples = [EvaluationSample(query="q", contexts=["c"], response="r", sample_id="s1")]
    evaluator.evaluate(samples)

    assert "scoring_mode" in captured_prompts[0].lower() or "safety refusal" in captured_prompts[0].lower()


def test_aggregate_mixes_standard_and_refusal():
    judge = StubJudge([STANDARD_PAYLOAD, REFUSAL_PAYLOAD, STANDARD_PAYLOAD])
    evaluator = LLMJudgeEvaluator(judge=judge, thresholds={}, refusal_aware=True)

    samples = [
        EvaluationSample(query=f"q{i}", contexts=["c"], response="r", sample_id=f"s{i}")
        for i in range(3)
    ]
    result = evaluator.evaluate(samples)

    assert result.scoring_modes_count == {"standard": 2, "safety_refusal": 1}
    assert result.samples_evaluated == 3
