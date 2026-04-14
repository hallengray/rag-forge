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
from typing import Protocol, runtime_checkable


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
    ) -> None:
        self._judge = judge
        self.max_tokens = max_tokens
        self._system_prompt = system_prompt

    def generate_text(self, prompt: str) -> str:
        """Generate text using the underlying judge."""
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
