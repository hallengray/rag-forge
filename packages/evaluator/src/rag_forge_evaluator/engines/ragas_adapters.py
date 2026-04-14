"""Wrappers that implement ragas's LLM and Embeddings interfaces around
rag-forge's own Judge abstraction.

Design rationale: the previous adapter let ragas pick its own default
LLM + embeddings, which changed between ragas versions and hardcoded
gpt-4o-mini for faithfulness extraction. By injecting our own wrappers
we honor --judge claude end-to-end and stay version-stable across ragas
releases.

ragas 0.4.x contract (from src/ragas/llms/base.py)::

    class BaseRagasLLM(ABC):
        def generate_text(
            self,
            prompt: PromptValue,
            n: int = 1,
            temperature: float | None = 0.01,
            stop: list[str] | None = None,
            callbacks: Callbacks = None,
        ) -> LLMResult: ...

        async def agenerate_text(...) -> LLMResult: ...

Our wrappers implement the full signature so ragas receives exactly what
its internal metric implementations expect, rather than duck-typing a
narrow subset that may break on minor version bumps. ``n``, ``temperature``,
``stop``, and ``callbacks`` are accepted for contract compatibility but
currently forwarded to the underlying rag-forge Judge only insofar as the
Judge interface supports them — the Judge protocol is a simple
``(system_prompt, user_prompt) -> str`` call, so extra kwargs are
gracefully ignored.

ragas and langchain imports are deferred into method bodies so this
module stays importable without either installed — unit tests run
without the optional extras.
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from langchain_core.callbacks import Callbacks
    from langchain_core.outputs import LLMResult

_REFUSAL_NOTE = (
    "NOTE: If the retrieved context lacks sufficient information to answer the question, "
    "and the response is a valid safety refusal (declining to fabricate), score faithfulness "
    "and hallucination at 1.0 — the refusal is correct behavior.\n\n"
)


@runtime_checkable
class _JudgeLike(Protocol):
    """Protocol matching rag-forge's Judge interface."""

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt to the judge and return the response text."""
        ...

    def model_name(self) -> str:
        """Return the name of the judge model."""
        ...


def _prompt_to_str(prompt: Any) -> str:
    """Extract a plain string from a ragas/langchain ``PromptValue`` or a raw string.

    ragas 0.4.x passes ``langchain_core.prompt_values.PromptValue`` instances
    (which have ``.to_string()``). Tests may pass raw strings; we accept both.
    """
    if isinstance(prompt, str):
        return prompt
    to_string = getattr(prompt, "to_string", None)
    if callable(to_string):
        return str(to_string())
    return str(prompt)


def _wrap_as_llm_result(text: str) -> LLMResult:
    """Wrap a plain string response in a langchain ``LLMResult``.

    ragas 0.4.x expects ``generate_text`` / ``agenerate_text`` to return an
    ``LLMResult`` whose ``.generations[0][0].text`` holds the generated text.
    We defer the imports so unit tests without langchain installed keep
    working — they pass raw strings directly and inspect the ``.generations``
    attribute through the duck-typed return value.
    """
    from langchain_core.outputs import Generation
    from langchain_core.outputs import LLMResult as _LLMResult

    return _LLMResult(generations=[[Generation(text=text)]])


class RagForgeRagasLLM:
    """ragas LLM wrapper that forwards to a rag-forge Judge.

    Implements the full ragas 0.4.x ``BaseRagasLLM`` contract including the
    extra ``n`` / ``temperature`` / ``stop`` / ``callbacks`` kwargs that ragas
    passes through from its internal metric prompts. ``max_tokens`` is
    retained on the instance so future Judge-protocol extensions can pick
    it up; the current Judge interface does not accept it, so the underlying
    model's own max-tokens default applies.

    The class does NOT subclass ``BaseRagasLLM`` because that would force a
    hard import of ragas at module load time and break unit tests on
    machines without the ``[ragas]`` extra installed. It implements the
    duck-typed contract — ragas only calls ``generate_text`` /
    ``agenerate_text`` / ``model_name``, all of which we provide with
    correct signatures and return types.
    """

    def __init__(
        self,
        judge: _JudgeLike,
        max_tokens: int = 8192,
        system_prompt: str = "",
        refusal_aware: bool = True,
    ) -> None:
        self._judge = judge
        self.max_tokens = max_tokens
        self._system_prompt = system_prompt
        self._refusal_aware = refusal_aware

    def _complete(self, prompt: Any) -> str:
        """Internal: extract text, inject refusal note, call judge."""
        prompt_text = _prompt_to_str(prompt)
        if self._refusal_aware:
            prompt_text = _REFUSAL_NOTE + prompt_text
        return self._judge.judge(self._system_prompt, prompt_text)

    def generate_text(
        self,
        prompt: Any,
        n: int = 1,
        temperature: float | None = 0.01,
        stop: list[str] | None = None,
        callbacks: Callbacks | None = None,
    ) -> Any:
        """Sync ragas ``generate_text`` implementation.

        Signature matches ``BaseRagasLLM.generate_text`` in ragas 0.4.x so
        the adapter cannot be silently broken by ragas adding kwargs. ``n``,
        ``temperature``, ``stop``, and ``callbacks`` are accepted for
        contract compatibility; only the prompt text and the configured
        system prompt are forwarded to the underlying Judge. The return
        value is a langchain ``LLMResult`` when langchain is installed
        (the production path used by ragas), or a duck-typed object with
        the same ``.generations[0][0].text`` shape otherwise.
        """
        _ = n, temperature, stop, callbacks  # contract-only parameters
        text = self._complete(prompt)
        try:
            return _wrap_as_llm_result(text)
        except ImportError:
            # Unit tests without langchain installed: return a minimal
            # duck-typed object so the test can still inspect the result.
            return _StringLLMResult(text)

    async def agenerate_text(
        self,
        prompt: Any,
        n: int = 1,
        temperature: float | None = 0.01,
        stop: list[str] | None = None,
        callbacks: Callbacks | None = None,
    ) -> Any:
        """Async variant of ``generate_text``.

        Runs the sync path in a worker thread — our underlying Judge
        implementations are synchronous, and ragas parallelizes metrics
        at a higher level anyway.
        """
        return await asyncio.to_thread(
            self.generate_text, prompt, n, temperature, stop, callbacks
        )

    def model_name(self) -> str:
        """Return the model name from the underlying judge."""
        return self._judge.model_name()


class _StringLLMResult:
    """Minimal duck-typed stand-in for ``langchain_core.outputs.LLMResult``.

    Returned by ``RagForgeRagasLLM.generate_text`` only when langchain is not
    installed — e.g. in unit tests that assert on the returned text without
    pulling the langchain dependency. Production ragas runs get a real
    ``LLMResult`` via ``_wrap_as_llm_result``.
    """

    def __init__(self, text: str) -> None:
        self._text = text
        self.generations = [[_StringGeneration(text)]]

    @property
    def text(self) -> str:
        return self._text

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._text == other
        if isinstance(other, _StringLLMResult):
            return self._text == other._text
        return NotImplemented

    def __str__(self) -> str:
        return self._text


class _StringGeneration:
    """Minimal langchain ``Generation`` stand-in — see ``_StringLLMResult``."""

    def __init__(self, text: str) -> None:
        self.text = text


EmbeddingProvider = Literal["openai", "voyage", "mock"]


def _openai_client() -> Any:
    """Lazy-import the OpenAI client so unit tests don't require the SDK
    unless the openai provider is actually used. Wrapped in a function
    so tests can monkeypatch it."""
    from openai import OpenAI

    return OpenAI()


def _voyage_client() -> Any:
    """Lazy-import the Voyage client. Raises ImportError if voyageai is
    not installed — users need the [ragas-voyage] extra."""
    try:
        import voyageai
    except ImportError as exc:  # pragma: no cover
        msg = (
            "Voyage embeddings requested but voyageai is not installed. "
            "Install with: pip install rag-forge-evaluator[ragas-voyage]"
        )
        raise ImportError(msg) from exc
    return voyageai.Client()


class RagForgeRagasEmbeddings:
    """ragas embeddings wrapper with pluggable provider.

    Three providers:
    - ``openai``: text-embedding-3-small via the openai SDK
    - ``voyage``: voyage-3 via the voyageai SDK (requires ``[ragas-voyage]`` extra)
    - ``mock``: deterministic hash-based vectors for tests — no network

    Implements the ragas 0.4.x ``BaseRagasEmbeddings`` contract including
    both sync (``embed_query`` / ``embed_documents``) and async
    (``aembed_query`` / ``aembed_documents``) methods.
    """

    _MOCK_DIM = 8
    _OPENAI_MODEL = "text-embedding-3-small"
    _VOYAGE_MODEL = "voyage-3"

    def __init__(
        self,
        provider: EmbeddingProvider = "openai",
        model: str | None = None,
    ) -> None:
        if provider not in ("openai", "voyage", "mock"):
            msg = f"Unknown embeddings provider: {provider!r}. Use openai, voyage, or mock."
            raise ValueError(msg)
        self._provider = provider
        self._model = model

    def embed_query(self, text: str) -> list[float]:
        if self._provider == "mock":
            return self._mock_embed(text)
        if self._provider == "openai":
            client = _openai_client()
            resp = client.embeddings.create(
                model=self._model or self._OPENAI_MODEL,
                input=text,
            )
            return list(resp.data[0].embedding)
        if self._provider == "voyage":
            client = _voyage_client()
            resp = client.embed(
                texts=[text],
                model=self._model or self._VOYAGE_MODEL,
            )
            return list(resp.embeddings[0])
        raise RuntimeError(f"unreachable: {self._provider}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._provider == "mock":
            return [self._mock_embed(t) for t in texts]
        if self._provider == "openai":
            client = _openai_client()
            resp = client.embeddings.create(
                model=self._model or self._OPENAI_MODEL,
                input=texts,
            )
            return [list(d.embedding) for d in resp.data]
        if self._provider == "voyage":
            client = _voyage_client()
            resp = client.embed(
                texts=texts,
                model=self._model or self._VOYAGE_MODEL,
            )
            return [list(e) for e in resp.embeddings]
        raise RuntimeError(f"unreachable: {self._provider}")

    async def aembed_query(self, text: str) -> list[float]:
        """Async variant of ``embed_query``.

        Our underlying SDK calls are synchronous, so we defer to a worker
        thread to honor ragas's async contract without blocking.
        """
        return await asyncio.to_thread(self.embed_query, text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Async variant of ``embed_documents``."""
        return await asyncio.to_thread(self.embed_documents, texts)

    @classmethod
    def _mock_embed(cls, text: str) -> list[float]:
        """Deterministic fake embedding: SHA-256 the text, take 8 bytes,
        normalize to floats in [0, 1]. Stable across runs so tests
        comparing vectors are reproducible."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[: cls._MOCK_DIM]]
