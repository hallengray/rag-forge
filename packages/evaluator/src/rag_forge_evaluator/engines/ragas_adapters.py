"""Wrappers that implement ragas's LLM and Embeddings interfaces around
rag-forge's own Judge abstraction.

Design rationale: the previous adapter let ragas pick its own default
LLM + embeddings, which changed between ragas versions and hardcoded
gpt-4o-mini for faithfulness extraction. By injecting our own wrappers
we honor --judge claude end-to-end and stay version-stable across ragas
releases.

ragas 0.4.x contract (from src/ragas/llms/base.py), full public surface
the wrapper must honour:

    class BaseRagasLLM(ABC):
        run_config: RunConfig

        # abstract — must be implemented
        def generate_text(self, prompt, n, temperature, stop, callbacks) -> LLMResult: ...
        async def agenerate_text(self, prompt, n, temperature, stop, callbacks) -> LLMResult: ...
        def is_finished(self, response: LLMResult) -> bool: ...

        # concrete helpers on the base class that ragas's metric code CALLS
        # on every LLM (not just ones that subclass BaseRagasLLM). A duck-
        # typed wrapper must reimplement these or it will crash the moment
        # a metric invokes them:
        async def generate(self, prompt, n, temperature, stop, callbacks) -> LLMResult: ...
        def get_temperature(self, n: int) -> float: ...
        def set_run_config(self, run_config: RunConfig) -> None: ...

    class BaseRagasEmbeddings(ABC):
        run_config: RunConfig
        def embed_query(self, text) -> list[float]: ...
        def embed_documents(self, texts) -> list[list[float]]: ...
        async def aembed_query(self, text) -> list[float]: ...
        async def aembed_documents(self, texts) -> list[list[float]]: ...
        def set_run_config(self, run_config: RunConfig) -> None: ...

``n``, ``temperature``, ``stop``, and ``callbacks`` are accepted for
contract compatibility but currently forwarded to the underlying rag-forge
Judge only insofar as the Judge interface supports them — the Judge
protocol is a simple ``(system_prompt, user_prompt) -> str`` call, so
extra kwargs are gracefully ignored.

**History:** v0.2.0 shipped only ``generate_text`` / ``agenerate_text`` /
``model_name`` under the assumption those were the only methods ragas
called on an LLM. The Cycle 3 PearMedica audit (2026-04-15) proved that
assumption wrong — ragas's metric code calls the concrete
``BaseRagasLLM.generate`` wrapper, which in turn calls ``agenerate_text``
with retry. v0.2.2 adds the missing ``generate`` / ``get_temperature`` /
``is_finished`` / ``set_run_config`` shims so the duck-typed wrapper
matches the full base-class surface. A contract test in
``tests/test_ragas_adapters_contract.py`` now iterates every public method
on ``BaseRagasLLM`` and ``BaseRagasEmbeddings`` and asserts each is
implemented, so this class of bug cannot silently ship again.

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
    passes through from its internal metric prompts.

    **Per-call ``max_tokens`` forwarding is a v0.2.1 follow-up.** The current
    ``Judge`` protocol is ``(system_prompt, user_prompt) -> str`` and does
    not accept per-call token caps, so the underlying model's own default
    applies. For Claude this is 4096 tokens by default (raisable via the
    ``RAG_FORGE_JUDGE_MAX_TOKENS`` environment variable, which ClaudeJudge
    honors at construction). The Cycle 2 truncation bug that
    motivated a configurable max_tokens was fixed upstream in ClaudeJudge
    by raising its default from 1024 → 4096, so most clinical/structured
    workloads no longer need per-call override.

    The class does NOT subclass ``BaseRagasLLM`` because that would force a
    hard import of ragas at module load time and break unit tests on
    machines without the ``[ragas]`` extra installed. It implements the
    duck-typed contract by re-declaring every public method ragas calls —
    see the module docstring for the full surface. The contract test at
    ``tests/test_ragas_adapters_contract.py`` is the tripwire that keeps
    this in sync with future ragas releases.
    """

    def __init__(
        self,
        judge: _JudgeLike,
        system_prompt: str = "",
        refusal_aware: bool = True,
    ) -> None:
        self._judge = judge
        self._system_prompt = system_prompt
        self._refusal_aware = refusal_aware
        self.run_config: Any = None

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

    async def generate(
        self,
        prompt: Any,
        n: int = 1,
        temperature: float | None = None,
        stop: list[str] | None = None,
        callbacks: Callbacks | None = None,
    ) -> Any:
        """Async concrete shim that mirrors ``BaseRagasLLM.generate``.

        ragas's metric code calls ``await llm.generate(prompt, ...)`` on
        every LLM, regardless of whether the LLM subclasses
        ``BaseRagasLLM``. Because this wrapper is duck-typed (see class
        docstring for why we do not subclass), we must re-declare
        ``generate`` here or every RAGAS evaluation crashes on first job
        with ``AttributeError: no attribute 'generate'`` — the Cycle 3
        regression that motivated v0.2.2.

        Implementation mirrors the base-class behaviour: resolve a
        temperature default, delegate to ``agenerate_text``, then run
        ``is_finished`` so ragas's retry / error surface behaves the
        same. We intentionally skip the base class's ``add_async_retry``
        wrapper — our underlying Judge implementations already own their
        own retry policy (see e.g. ClaudeJudge's 529 handling) and
        double-wrapping leads to retry storms.
        """
        if temperature is None:
            temperature = self.get_temperature(n)
        result = await self.agenerate_text(
            prompt,
            n=n,
            temperature=temperature,
            stop=stop,
            callbacks=callbacks,
        )
        if not self.is_finished(result):
            msg = (
                "RagForgeRagasLLM.generate: underlying judge response did "
                "not finish cleanly (is_finished == False). This is a "
                "defensive check; override is_finished if your Judge "
                "exposes a real finish signal."
            )
            raise RuntimeError(msg)
        return result

    def is_finished(self, response: Any) -> bool:
        """Report whether a generation finished cleanly.

        ragas uses this to decide whether to retry on truncation. Our
        Judge protocol does not currently expose a finish-reason, so we
        conservatively report True — the underlying Judge implementation
        is responsible for retrying on truncation (see Cycle 2 Finding
        #5 and the ClaudeJudge ``max_tokens`` raise).

        If a future Judge exposes a finish-reason signal, this method is
        the place to propagate it.
        """
        _ = response
        return True

    def get_temperature(self, n: int) -> float:
        """Return a sampling temperature given the requested ``n``.

        Matches ragas's own convention: near-deterministic for a single
        sample, warmer when the caller asks for multiple. ragas uses
        this to diversify samples for metrics that rely on sampling
        stability (e.g. ``answer_correctness``).
        """
        return 0.01 if n <= 1 else 0.3

    def set_run_config(self, run_config: Any) -> None:
        """Store a ragas ``RunConfig`` for later use.

        ragas's evaluation runner injects its ``RunConfig`` (timeouts,
        retry budgets, worker counts) into every LLM and embeddings
        wrapper before kicking off metric jobs. We store it for contract
        compatibility; our actual execution path honours the Judge's
        own timeout/retry configuration rather than ragas's.
        """
        self.run_config = run_config


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
        self.run_config: Any = None

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

    def set_run_config(self, run_config: Any) -> None:
        """Store a ragas ``RunConfig`` for contract compatibility.

        See ``RagForgeRagasLLM.set_run_config`` for rationale.
        """
        self.run_config = run_config

    def embed_text(self, text: str, is_async: bool = True) -> list[float]:
        """Dispatch helper that ragas's concrete ``BaseRagasEmbeddings``
        exposes alongside ``embed_query``. Some metrics call ``embed_text``
        instead of ``embed_query`` — they are conceptually the same, just
        different entry points. We forward to ``embed_query`` for the
        sync path and to ``aembed_query`` when ``is_async=True``.

        ``is_async=True`` is the base-class default, so we match it — but
        because our underlying Judge/embedding clients are synchronous,
        the "async" path just runs the sync call in a worker thread
        (same pattern as ``aembed_query``).
        """
        if is_async:
            return asyncio.run(self.aembed_query(text))
        return self.embed_query(text)

    def embed_texts(self, texts: list[str], is_async: bool = True) -> list[list[float]]:
        """Batch variant of ``embed_text`` — same dispatch semantics."""
        if is_async:
            return asyncio.run(self.aembed_documents(texts))
        return self.embed_documents(texts)

    @classmethod
    def _mock_embed(cls, text: str) -> list[float]:
        """Deterministic fake embedding: SHA-256 the text, take 8 bytes,
        normalize to floats in [0, 1]. Stable across runs so tests
        comparing vectors are reproducible."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[: cls._MOCK_DIM]]
