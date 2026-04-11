"""Deterministic mock judge for testing. Returns configurable fixed responses."""
import json

_DEFAULT_RESPONSE = json.dumps({
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
