"""Judge clients must be configurable for retries, max_tokens, and model.

These tests guard the generalization fixes from the 2026-04-13 cycle-1
audit: hardcoded retry counts and hardcoded 1024-token output budgets
broke for any customer with a long-response RAG pipeline.
"""
from unittest.mock import patch

import pytest

from rag_forge_evaluator.judge.claude_judge import ClaudeJudge
from rag_forge_evaluator.judge.openai_judge import OpenAIJudge

# ---------- max_retries ----------


def test_claude_judge_default_max_retries_is_5() -> None:
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls:
        ClaudeJudge(api_key="test-key")
        kwargs = mock_cls.call_args.kwargs
        assert kwargs.get("max_retries") == 5


def test_openai_judge_default_max_retries_is_5() -> None:
    with patch("rag_forge_evaluator.judge.openai_judge.OpenAI") as mock_cls:
        OpenAIJudge(api_key="test-key")
        kwargs = mock_cls.call_args.kwargs
        assert kwargs.get("max_retries") == 5


def test_claude_judge_constructor_arg_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAG_FORGE_JUDGE_MAX_RETRIES", raising=False)
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls:
        ClaudeJudge(api_key="test-key", max_retries=10)
        assert mock_cls.call_args.kwargs.get("max_retries") == 10


def test_claude_judge_env_var_sets_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_MAX_RETRIES", "8")
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls:
        ClaudeJudge(api_key="test-key")
        assert mock_cls.call_args.kwargs.get("max_retries") == 8


def test_openai_judge_env_var_sets_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_MAX_RETRIES", "7")
    with patch("rag_forge_evaluator.judge.openai_judge.OpenAI") as mock_cls:
        OpenAIJudge(api_key="test-key")
        assert mock_cls.call_args.kwargs.get("max_retries") == 7


def test_constructor_arg_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_MAX_RETRIES", "3")
    with patch("rag_forge_evaluator.judge.claude_judge.Anthropic") as mock_cls:
        ClaudeJudge(api_key="test-key", max_retries=9)
        assert mock_cls.call_args.kwargs.get("max_retries") == 9


# ---------- max_tokens ----------


def test_claude_judge_default_max_tokens_is_4096(monkeypatch: pytest.MonkeyPatch) -> None:
    """cycle-1 audit truncated mid-array at 1024. New default is 4096.

    Bumping the default fixes the ~50% parse-failure rate on
    faithfulness/hallucination metrics for long structured responses.
    """
    monkeypatch.delenv("RAG_FORGE_JUDGE_MAX_TOKENS", raising=False)
    judge = ClaudeJudge(api_key="test-key")
    assert judge._max_tokens == 4096


def test_openai_judge_default_max_tokens_is_4096(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAG_FORGE_JUDGE_MAX_TOKENS", raising=False)
    judge = OpenAIJudge(api_key="test-key")
    assert judge._max_tokens == 4096


def test_claude_judge_max_tokens_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_MAX_TOKENS", "8192")
    judge = ClaudeJudge(api_key="test-key")
    assert judge._max_tokens == 8192


def test_claude_judge_max_tokens_constructor_arg_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_MAX_TOKENS", "8192")
    judge = ClaudeJudge(api_key="test-key", max_tokens=2048)
    assert judge._max_tokens == 2048


# ---------- model name ----------


def test_claude_judge_accepts_custom_model() -> None:
    judge = ClaudeJudge(api_key="test-key", model="claude-opus-4-6")
    assert judge.model_name() == "claude-opus-4-6"


def test_openai_judge_accepts_custom_model() -> None:
    judge = OpenAIJudge(api_key="test-key", model="gpt-4-turbo")
    assert judge.model_name() == "gpt-4-turbo"


def test_claude_judge_model_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_MODEL", "claude-haiku-4-5")
    judge = ClaudeJudge(api_key="test-key")
    assert judge.model_name() == "claude-haiku-4-5"


def test_openai_judge_model_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_MODEL", "gpt-4o-mini")
    judge = OpenAIJudge(api_key="test-key")
    assert judge.model_name() == "gpt-4o-mini"


def test_claude_judge_constructor_model_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_FORGE_JUDGE_MODEL", "claude-haiku-4-5")
    judge = ClaudeJudge(api_key="test-key", model="claude-opus-4-6")
    assert judge.model_name() == "claude-opus-4-6"


# ---------- validation ----------


def test_claude_judge_rejects_zero_max_tokens() -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        ClaudeJudge(api_key="test-key", max_tokens=0)


def test_claude_judge_rejects_negative_max_tokens() -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        ClaudeJudge(api_key="test-key", max_tokens=-1)


def test_claude_judge_rejects_zero_max_retries() -> None:
    with pytest.raises(ValueError, match="max_retries"):
        ClaudeJudge(api_key="test-key", max_retries=0)


def test_openai_judge_rejects_zero_max_tokens() -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        OpenAIJudge(api_key="test-key", max_tokens=0)


def test_openai_judge_rejects_negative_max_retries() -> None:
    with pytest.raises(ValueError, match="max_retries"):
        OpenAIJudge(api_key="test-key", max_retries=-1)
