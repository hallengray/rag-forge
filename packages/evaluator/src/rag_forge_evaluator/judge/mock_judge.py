"""Deterministic mock judge for testing. Returns configurable fixed responses."""
import json

_DEFAULT_RESPONSE = json.dumps({
    # Combined-path fields (v0.2.0+) — consumed by LLMJudgeEvaluator when
    # using the default four metrics. Scores chosen to comfortably clear
    # all four default thresholds (faithfulness 0.85, answer_relevance 0.80,
    # context_relevance 0.80, hallucination 0.95) so mock-judge CI runs
    # exercise the "passing pipeline" code path.
    "scoring_mode": "standard",
    "refusal_justification": None,
    "faithfulness": 0.9,
    "answer_relevance": 0.88,
    "context_relevance": 0.85,
    "hallucination": 0.97,
    # Legacy per-metric fields — consumed by the individual metric
    # evaluators on the per-metric code path (used when a caller supplies
    # a custom metrics list, e.g. the partial-report tests).
    "claims": [
        {"text": "claim 1", "supported": True},
        {"text": "claim 2", "supported": True},
    ],
    "score": 0.9,
    "ratings": [{"chunk_index": 0, "score": 4, "reason": "relevant"}],
    "mean_score": 0.8,
    "completeness": 4,
    "correctness": 4,
    "coherence": 4,
    "overall_score": 0.8,
    "unsupported_count": 0,
    "total_claims": 2,
    "hallucination_rate": 0.0,
})


class MockJudge:
    """Returns deterministic JSON for all judge calls. Used in all tests."""

    def __init__(self, fixed_response: str | None = None) -> None:
        self._response = fixed_response or _DEFAULT_RESPONSE

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        _ = system_prompt, user_prompt
        return self._response

    def model_name(self) -> str:
        return "mock-judge"
