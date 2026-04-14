"""Tests for ragas adapter wrappers."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from rag_forge_evaluator.engines.ragas_adapters import RagForgeRagasLLM, RagForgeRagasEmbeddings


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


def test_embeddings_mock_provider_returns_deterministic_vector():
    embed = RagForgeRagasEmbeddings(provider="mock")
    v1 = embed.embed_query("hello")
    v2 = embed.embed_query("hello")
    v3 = embed.embed_query("world")
    assert isinstance(v1, list)
    assert len(v1) == 8
    assert v1 == v2
    assert v1 != v3


def test_embeddings_mock_batch_returns_one_per_input():
    embed = RagForgeRagasEmbeddings(provider="mock")
    vectors = embed.embed_documents(["a", "b", "c"])
    assert len(vectors) == 3
    assert all(len(v) == 8 for v in vectors)


def test_embeddings_openai_provider_calls_openai_client():
    fake_client = MagicMock()
    fake_client.embeddings.create.return_value.data = [MagicMock(embedding=[0.1, 0.2])]

    with patch("rag_forge_evaluator.engines.ragas_adapters._openai_client", return_value=fake_client):
        embed = RagForgeRagasEmbeddings(provider="openai")
        result = embed.embed_query("hello")

    assert result == [0.1, 0.2]
    fake_client.embeddings.create.assert_called_once()
    call = fake_client.embeddings.create.call_args
    assert call.kwargs["model"] == "text-embedding-3-small"
    assert call.kwargs["input"] == "hello"


def test_embeddings_voyage_provider_calls_voyage_client():
    fake_client = MagicMock()
    fake_client.embed.return_value.embeddings = [[0.3, 0.4]]

    with patch("rag_forge_evaluator.engines.ragas_adapters._voyage_client", return_value=fake_client):
        embed = RagForgeRagasEmbeddings(provider="voyage")
        result = embed.embed_query("hello")

    assert result == [0.3, 0.4]
    fake_client.embed.assert_called_once()
    call = fake_client.embed.call_args
    assert call.kwargs["model"] == "voyage-3"


def test_embeddings_invalid_provider_raises():
    import pytest
    with pytest.raises(ValueError, match="Unknown embeddings provider"):
        RagForgeRagasEmbeddings(provider="unsupported")  # type: ignore[arg-type]
