"""Tests for ragas adapter wrappers."""

import asyncio
from unittest.mock import MagicMock

import pytest

from rag_forge_evaluator.engines.ragas_adapters import RagForgeRagasLLM


class FakeJudge:
    def __init__(self, response: str = '{"ok": true}') -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self._response

    def model_name(self) -> str:
        return "fake-judge-v1"


def test_wrapper_forwards_generate_text_to_judge():
    judge = FakeJudge(response="faithful")
    llm = RagForgeRagasLLM(judge=judge, max_tokens=8192)
    result = llm.generate_text("What is the capital of France?")
    assert result == "faithful"
    assert judge.calls[0][1] == "What is the capital of France?"


def test_wrapper_reports_judge_model_name():
    llm = RagForgeRagasLLM(judge=FakeJudge(), max_tokens=8192)
    assert llm.model_name() == "fake-judge-v1"


def test_wrapper_exposes_max_tokens_attribute():
    llm = RagForgeRagasLLM(judge=FakeJudge(), max_tokens=4096)
    assert llm.max_tokens == 4096


def test_wrapper_uses_empty_system_prompt_by_default():
    judge = FakeJudge()
    llm = RagForgeRagasLLM(judge=judge, max_tokens=8192)
    llm.generate_text("hello")
    assert judge.calls[0][0] == ""


def test_wrapper_async_generate_text():
    """Test async generate_text using asyncio.run to avoid pytest-asyncio dependency."""
    judge = FakeJudge(response="async-ok")
    llm = RagForgeRagasLLM(judge=judge, max_tokens=8192)
    result = asyncio.run(llm.agenerate_text("ping"))
    assert result == "async-ok"
    assert judge.calls[0][1] == "ping"
