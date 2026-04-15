"""Tests for ragas adapter wrappers."""

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from rag_forge_evaluator.engines.ragas_adapters import (
    RagForgeRagasEmbeddings,
    RagForgeRagasLLM,
)


def _llm_result_text(result: Any) -> str:
    """Extract the generated text from either a real langchain ``LLMResult``
    or the ``_StringLLMResult`` stub used when langchain is not installed.

    Tests need to assert against the judge's response regardless of which
    environment they run in — langchain-core comes in with the ``[ragas]``
    extra, so on CI with the extra installed we get real LLMResults, and
    without it we get the duck-typed stub.
    """
    if isinstance(result, str):
        return result
    return str(result.generations[0][0].text)


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
    llm = RagForgeRagasLLM(judge=judge, refusal_aware=False)
    result = llm.generate_text("What is the capital of France?")
    assert _llm_result_text(result) == "faithful"
    assert judge.calls[0][1] == "What is the capital of France?"


def test_wrapper_reports_judge_model_name():
    llm = RagForgeRagasLLM(judge=FakeJudge())
    assert llm.model_name() == "fake-judge-v1"


def test_wrapper_uses_empty_system_prompt_by_default():
    judge = FakeJudge()
    llm = RagForgeRagasLLM(judge=judge)
    llm.generate_text("hello")
    assert judge.calls[0][0] == ""


def test_wrapper_async_generate_text():
    """Test async generate_text using asyncio.run to avoid pytest-asyncio dependency."""
    judge = FakeJudge(response="async-ok")
    llm = RagForgeRagasLLM(judge=judge, refusal_aware=False)
    result = asyncio.run(llm.agenerate_text("ping"))
    assert _llm_result_text(result) == "async-ok"
    assert judge.calls[0][1] == "ping"


def test_wrapper_async_generate_forwards_to_agenerate_text():
    """The v0.2.2 ``generate`` shim. This is the method Cycle 3 caught
    missing — ragas's metric code calls ``await llm.generate(prompt)``
    and v0.2.1 crashed with AttributeError. Verifies the shim exists,
    is async, and threads the prompt all the way through to the judge."""
    judge = FakeJudge(response="generate-ok")
    llm = RagForgeRagasLLM(judge=judge, refusal_aware=False)
    result = asyncio.run(llm.generate("what is DKA?"))
    assert _llm_result_text(result) == "generate-ok"
    assert judge.calls[0][1] == "what is DKA?"


def test_wrapper_async_generate_resolves_default_temperature_when_none():
    """BaseRagasLLM.generate resolves ``temperature=None`` via
    ``get_temperature(n)`` before calling ``agenerate_text``. Our shim
    must match that behaviour so ragas callers that pass ``None`` don't
    blow up with a type error in downstream judge code.

    Asserts the fallback path was actually taken — not just that the
    call didn't raise. CodeRabbit on PR #36 pointed out the original
    weaker test would have passed even if ``get_temperature`` was
    never called, so we patch it and assert the invocation.
    """
    judge = FakeJudge(response="ok")
    llm = RagForgeRagasLLM(judge=judge, refusal_aware=False)
    with patch.object(
        llm, "get_temperature", wraps=llm.get_temperature
    ) as get_temp:
        result = asyncio.run(llm.generate("prompt", n=1, temperature=None))
    assert _llm_result_text(result) == "ok"
    get_temp.assert_called_once_with(1)


def test_wrapper_async_generate_keeps_explicit_temperature():
    """Inverse of the fallback test: when a concrete temperature is
    passed, the shim must NOT call ``get_temperature``. Guards against
    over-eager fallback firing on valid caller-supplied 0.0 / 0.01.
    """
    judge = FakeJudge(response="ok")
    llm = RagForgeRagasLLM(judge=judge, refusal_aware=False)
    with patch.object(llm, "get_temperature") as get_temp:
        result = asyncio.run(llm.generate("prompt", n=1, temperature=0.7))
    assert _llm_result_text(result) == "ok"
    get_temp.assert_not_called()


def test_wrapper_async_generate_n_greater_than_one_produces_fused_shape():
    """When ``n > 1``, ``generate`` must return an ``LLMResult`` with
    exactly N generations inside ``generations[0]`` — the shape ragas
    expects for multi-sample metrics (e.g. answer_correctness). CodeRabbit
    on PR #36 caught that the original shim ignored ``n`` and returned
    a single generation.

    Uses a thread-safe counting judge because
    ``RagForgeRagasLLM.generate`` fans the N calls out via
    ``asyncio.gather`` and each call runs in a separate worker thread
    (``asyncio.to_thread`` under the hood). A naive non-atomic
    ``counter += 1`` would race and produce duplicate sample labels
    or an undercounted total, flaking the test. CodeRabbit on PR #36
    round 2 caught this.
    """
    import threading as _threading

    counter = {"i": 0}
    lock = _threading.Lock()

    class CountingJudge:
        def judge(self, system_prompt: str, user_prompt: str) -> str:
            _ = system_prompt, user_prompt
            with lock:
                counter["i"] += 1
                return f"sample-{counter['i']}"

        def model_name(self) -> str:
            return "counting-judge"

    llm = RagForgeRagasLLM(judge=CountingJudge(), refusal_aware=False)
    result = asyncio.run(llm.generate("prompt", n=3, temperature=0.7))

    assert counter["i"] == 3, f"expected 3 judge calls, got {counter['i']}"

    assert hasattr(result, "generations"), "result missing .generations"
    outer = result.generations
    assert len(outer) == 1, f"outer length must be 1 (one prompt), got {len(outer)}"
    inner = outer[0]
    assert len(inner) == 3, f"inner length must be 3 (n=3 samples), got {len(inner)}"
    texts = {gen.text for gen in inner}
    assert texts == {"sample-1", "sample-2", "sample-3"}, (
        f"expected three distinct samples, got {texts}"
    )


def test_fuse_llm_results_raises_on_malformed_input():
    """``_fuse_llm_results`` must fail loud on malformed result shapes
    instead of silently collapsing to ``results[0]``. CodeRabbit on
    PR #36 round 2 pointed out that a silent fallback hides real
    ``n > 1`` correctness bugs — a single returned sample skews
    downstream ragas metrics with no signal.
    """
    from rag_forge_evaluator.engines.ragas_adapters import _fuse_llm_results

    class NotAnLLMResult:
        pass

    with pytest.raises(ValueError, match="malformed result"):
        _fuse_llm_results([NotAnLLMResult(), NotAnLLMResult()])

    class EmptyOuter:
        def __init__(self) -> None:
            self.generations: list[list[object]] = []

    with pytest.raises(ValueError, match="malformed result"):
        _fuse_llm_results([EmptyOuter(), EmptyOuter()])

    with pytest.raises(ValueError, match="empty results list"):
        _fuse_llm_results([])


def test_embeddings_embed_text_is_async_and_awaitable():
    """``BaseRagasEmbeddings.embed_text`` is async in ragas 0.4.x. Our
    shim must match so ragas's ``await embeddings.embed_text(...)``
    calls work inside the evaluation runner's event loop.

    v0.2.2 originally shipped ``embed_text`` as sync with
    ``asyncio.run(self.aembed_query(...))`` — which crashes any caller
    already inside an event loop with
    ``RuntimeError: asyncio.run() cannot be called from a running
    event loop``. CodeRabbit on PR #36 caught it.
    """
    import inspect as _inspect

    embed = RagForgeRagasEmbeddings(provider="mock")
    assert _inspect.iscoroutinefunction(embed.embed_text), (
        "embed_text must be async (coroutine function) to match "
        "BaseRagasEmbeddings.embed_text"
    )
    assert _inspect.iscoroutinefunction(embed.embed_texts), (
        "embed_texts must be async (coroutine function)"
    )
    # Round-trip through the async path.
    v = asyncio.run(embed.embed_text("hello"))
    assert isinstance(v, list)
    assert len(v) == 8
    vs = asyncio.run(embed.embed_texts(["a", "b"]))
    assert len(vs) == 2
    assert all(len(x) == 8 for x in vs)


def test_embeddings_embed_text_callable_from_running_event_loop():
    """Regression: the sync ``asyncio.run()`` implementation crashed
    with ``RuntimeError: asyncio.run() cannot be called from a running
    event loop``. This test exercises the exact code path by calling
    ``embed_text`` from inside a running loop (the setting ragas
    evaluation creates). It must complete without raising.
    """
    embed = RagForgeRagasEmbeddings(provider="mock")

    async def run_inside_loop() -> list[float]:
        return await embed.embed_text("hello")

    v = asyncio.run(run_inside_loop())
    assert isinstance(v, list)
    assert len(v) == 8


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
    with pytest.raises(ValueError, match="Unknown embeddings provider"):
        RagForgeRagasEmbeddings(provider="unsupported")  # type: ignore[arg-type]


def test_llm_wrapper_injects_refusal_note_when_enabled():
    from rag_forge_evaluator.engines.ragas_adapters import RagForgeRagasLLM

    captured: list[str] = []

    class CapturingJudge:
        def judge(self, s: str, u: str) -> str:
            captured.append(u)
            return "ok"

        def model_name(self) -> str:
            return "cap"

    llm = RagForgeRagasLLM(judge=CapturingJudge(), refusal_aware=True)
    llm.generate_text("What is the dose?")

    assert "safety refusal" in captured[0].lower() or "refusal is correct" in captured[0].lower()
    # The original prompt is still in there somewhere
    assert "What is the dose?" in captured[0]


def test_llm_wrapper_omits_refusal_note_when_disabled():
    from rag_forge_evaluator.engines.ragas_adapters import RagForgeRagasLLM

    captured: list[str] = []

    class CapturingJudge:
        def judge(self, s: str, u: str) -> str:
            captured.append(u)
            return "ok"

        def model_name(self) -> str:
            return "cap"

    llm = RagForgeRagasLLM(judge=CapturingJudge(), refusal_aware=False)
    llm.generate_text("What is the dose?")

    # The exact prompt should pass through untouched
    assert captured[0] == "What is the dose?"


def test_ragas_evaluator_threads_refusal_aware_into_wrapper():
    """RagasEvaluator(refusal_aware=True) should store the flag so the
    wrapper it later constructs honors it. We verify by inspecting the
    stored attribute — avoids needing real ragas installed."""
    from rag_forge_evaluator.engines.ragas_evaluator import RagasEvaluator
    from rag_forge_evaluator.judge.mock_judge import MockJudge

    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={},
        refusal_aware=True,
        embeddings_provider="mock",
    )

    assert evaluator._refusal_aware is True
