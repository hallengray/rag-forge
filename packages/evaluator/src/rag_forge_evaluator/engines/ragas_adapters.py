"""Wrappers that implement ragas's LLM and Embeddings interfaces around
rag-forge's own Judge abstraction.

Design rationale: the previous adapter let ragas pick its own default
LLM + embeddings, which changed between ragas versions and hardcoded
gpt-4o-mini for faithfulness extraction. By injecting our own wrappers
we honor --judge claude end-to-end, control max_tokens, and stay
version-stable across ragas releases.

Ragas imports are deferred into method bodies so this module remains
importable without ragas installed — matching the existing
ragas_evaluator.py pattern and keeping unit tests lightweight.
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any, Literal, Protocol, runtime_checkable

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


class RagForgeRagasLLM:
    """ragas LLM wrapper that forwards to a rag-forge Judge.

    Implements both sync (``generate_text``) and async (``agenerate_text``)
    interfaces that ragas 0.4.x calls internally. The async variant runs
    the sync path in a thread — the underlying Judge implementations are
    sync, and ragas parallelizes metrics at a higher level anyway.
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

    def generate_text(self, prompt: str) -> str:
        """Generate text using the underlying judge."""
        if self._refusal_aware:
            prompt = _REFUSAL_NOTE + prompt
        return self._judge.judge(self._system_prompt, prompt)

    async def agenerate_text(self, prompt: str) -> str:
        """Async variant of generate_text.

        Runs the sync path in a thread to maintain compatibility
        with ragas 0.4.x's async callsites.
        """
        return await asyncio.to_thread(self.generate_text, prompt)

    def model_name(self) -> str:
        """Return the model name from the underlying judge."""
        return self._judge.model_name()


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
    - ``voyage``: voyage-3 via the voyageai SDK (requires [ragas-voyage] extra)
    - ``mock``: deterministic hash-based vectors for tests — no network
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

    @classmethod
    def _mock_embed(cls, text: str) -> list[float]:
        """Deterministic fake embedding: SHA-256 the text, take 8 bytes,
        normalize to floats in [0, 1]. Stable across runs so tests
        comparing vectors are reproducible."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[: cls._MOCK_DIM]]
