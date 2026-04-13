"""Anthropic 529 Overloaded must be retried by the judge wrapper.

The Anthropic SDK's built-in retry loop covers 408/429/500/502/503/504
but not 529. A 529 during the PearMedica cycle-2 audit crashed the run
on sample 1. This guards the explicit 529-retry wrapper added in v0.1.2.
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest
from anthropic import APIStatusError

from rag_forge_evaluator.judge.claude_judge import (
    ClaudeJudge,
    OverloadBudgetExhaustedError,
)


def _make_overloaded_error() -> APIStatusError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=529, request=request)
    return APIStatusError("Overloaded", response=response, body=None)


def _make_success_response(text: str = "score: 0.9") -> MagicMock:
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


def test_claude_judge_retries_529_then_succeeds() -> None:
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls, \
         patch("rag_forge_evaluator.judge.claude_judge.time.sleep") as mock_sleep, \
         patch("rag_forge_evaluator.judge.claude_judge.time.monotonic", return_value=0.0):
        client = MagicMock()
        client.messages.create.side_effect = [
            _make_overloaded_error(),
            _make_success_response("ok"),
        ]
        mock_cls.return_value = client

        judge = ClaudeJudge(api_key="test-key", max_retries=5)
        result = judge.judge("sys", "user")

        assert result == "ok"
        assert client.messages.create.call_count == 2
        assert mock_sleep.call_count == 1


def test_claude_judge_raises_after_exhausting_529_retries() -> None:
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls, \
         patch("rag_forge_evaluator.judge.claude_judge.time.sleep"), \
         patch("rag_forge_evaluator.judge.claude_judge.time.monotonic", return_value=0.0):
        client = MagicMock()
        client.messages.create.side_effect = [_make_overloaded_error()] * 10
        mock_cls.return_value = client

        judge = ClaudeJudge(api_key="test-key", max_retries=3)

        with pytest.raises(OverloadBudgetExhaustedError) as exc_info:
            judge.judge("sys", "user")

        # Wrapped original is still the 529 APIStatusError
        assert isinstance(exc_info.value.original, APIStatusError)
        assert exc_info.value.original.status_code == 529
        # max_retries=3 → 4 total attempts (initial + 3 retries)
        assert client.messages.create.call_count == 4
        assert exc_info.value.attempts == 4


def test_claude_judge_on_retry_callback_fires_with_attempt_and_elapsed() -> None:
    """The on_retry callback receives (attempt, elapsed, budget) on every retry."""
    observed: list[tuple[int, float, float]] = []

    def recorder(attempt: int, elapsed: float, budget: float) -> None:
        observed.append((attempt, elapsed, budget))

    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls, \
         patch("rag_forge_evaluator.judge.claude_judge.time.sleep"), \
         patch(
             "rag_forge_evaluator.judge.claude_judge.time.monotonic",
             side_effect=[0.0, 2.0, 6.0, 14.0],
         ):
        client = MagicMock()
        client.messages.create.side_effect = [
            _make_overloaded_error(),
            _make_overloaded_error(),
            _make_success_response("done"),
        ]
        mock_cls.return_value = client

        judge = ClaudeJudge(
            api_key="test-key",
            max_retries=5,
            overload_budget_seconds=300.0,
            on_retry=recorder,
        )
        assert judge.judge("sys", "user") == "done"

    assert len(observed) == 2
    assert observed[0][0] == 1
    assert observed[1][0] == 2
    assert all(budget == 300.0 for _, _, budget in observed)


def test_claude_judge_overload_budget_env_var_honored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_OVERLOAD_BUDGET_SECONDS", "45")
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic"):
        judge = ClaudeJudge(api_key="test-key")
        assert judge._overload_budget_seconds == 45.0


def test_claude_judge_overload_budget_constructor_arg_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_OVERLOAD_BUDGET_SECONDS", "45")
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic"):
        judge = ClaudeJudge(api_key="test-key", overload_budget_seconds=120.0)
        assert judge._overload_budget_seconds == 120.0


def test_claude_judge_budget_exhausts_before_max_retries() -> None:
    """If the budget is small enough, it trips before the attempt cap."""
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls, \
         patch("rag_forge_evaluator.judge.claude_judge.time.sleep"), \
         patch(
             "rag_forge_evaluator.judge.claude_judge.time.monotonic",
             side_effect=[0.0, 2.5, 7.0, 16.0],
         ):
        client = MagicMock()
        client.messages.create.side_effect = [_make_overloaded_error()] * 20
        mock_cls.return_value = client

        # max_retries=20 would allow many attempts, but budget=10s stops it early.
        judge = ClaudeJudge(
            api_key="test-key",
            max_retries=20,
            overload_budget_seconds=10.0,
        )

        with pytest.raises(OverloadBudgetExhaustedError) as exc_info:
            judge.judge("sys", "user")

        assert exc_info.value.budget_seconds == 10.0
        # Budget tripped early — far fewer attempts than max_retries=20 would allow
        assert client.messages.create.call_count < 10


def test_claude_judge_does_not_retry_non_529_api_errors() -> None:
    """A 400 Bad Request must propagate immediately — no retries."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    bad_request = APIStatusError(
        "Bad Request",
        response=httpx.Response(status_code=400, request=request),
        body=None,
    )
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls, \
         patch("rag_forge_evaluator.judge.claude_judge.time.sleep") as mock_sleep:
        client = MagicMock()
        client.messages.create.side_effect = bad_request
        mock_cls.return_value = client

        judge = ClaudeJudge(api_key="test-key", max_retries=5)

        with pytest.raises(APIStatusError) as exc_info:
            judge.judge("sys", "user")

        assert exc_info.value.status_code == 400
        assert client.messages.create.call_count == 1
        assert mock_sleep.call_count == 0
