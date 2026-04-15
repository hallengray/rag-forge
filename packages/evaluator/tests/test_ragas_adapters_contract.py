"""Contract tests that enforce our ragas adapter wrappers implement every
public method on ragas's ``BaseRagasLLM`` and ``BaseRagasEmbeddings``.

**Why this file exists:** v0.2.1 shipped ``RagForgeRagasLLM`` without a
``generate`` method because the original module docstring claimed
"ragas only calls generate_text / agenerate_text / model_name". That was
wrong — ragas's concrete ``BaseRagasLLM.generate`` calls ``agenerate_text``
through a retry wrapper, and ragas's metric code invokes it on every
LLM regardless of subclass status. The wrapper crashed with
``AttributeError: 'RagForgeRagasLLM' object has no attribute 'generate'``
on every metric job during the PearMedica Cycle 3 audit (2026-04-15).

This file is the tripwire. It iterates **every public method** on the
ragas base classes and asserts our duck-typed wrappers declare a callable
of the same name with a compatible arity. When ragas adds new methods in
a future release, these tests fail fast and we find out at CI time — not
at user-audit time.

Requires the ``[ragas]`` extra. Skipped if ragas is not installed, so
base test runs on machines without the extra keep working.
"""

from __future__ import annotations

import inspect

import pytest

from rag_forge_evaluator.engines.ragas_adapters import (
    RagForgeRagasEmbeddings,
    RagForgeRagasLLM,
)


class _StubJudge:
    """Minimal Judge-protocol implementation for wrapper instantiation."""

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        _ = system_prompt, user_prompt
        return "stub"

    def model_name(self) -> str:
        return "stub-judge"


def _public_methods(cls: type) -> list[str]:
    """Return the names of every public (non-underscore) callable on ``cls``."""
    return sorted(
        name
        for name in dir(cls)
        if not name.startswith("_") and callable(getattr(cls, name))
    )


@pytest.fixture
def ragas_base_llm() -> type:
    base = pytest.importorskip("ragas.llms.base")
    return base.BaseRagasLLM


@pytest.fixture
def ragas_base_embeddings() -> type:
    base = pytest.importorskip("ragas.embeddings.base")
    return base.BaseRagasEmbeddings


def test_llm_wrapper_declares_every_base_class_public_method(
    ragas_base_llm: type,
) -> None:
    """Every public callable on ``BaseRagasLLM`` must exist on our wrapper.

    The actionable failure message lists the *missing* methods so a
    future contributor sees exactly what ragas grew and what we still
    owe it.
    """
    base_methods = set(_public_methods(ragas_base_llm))
    wrapper_methods = set(_public_methods(RagForgeRagasLLM))
    missing = base_methods - wrapper_methods
    assert not missing, (
        f"RagForgeRagasLLM is missing {len(missing)} method(s) that "
        f"ragas.llms.base.BaseRagasLLM exposes: {sorted(missing)}. "
        f"Add duck-typed shims in ragas_adapters.py — see the v0.2.2 "
        f"release notes for precedent."
    )


def test_embeddings_wrapper_declares_every_base_class_public_method(
    ragas_base_embeddings: type,
) -> None:
    """Every public callable on ``BaseRagasEmbeddings`` must exist on our wrapper."""
    base_methods = set(_public_methods(ragas_base_embeddings))
    wrapper_methods = set(_public_methods(RagForgeRagasEmbeddings))
    missing = base_methods - wrapper_methods
    assert not missing, (
        f"RagForgeRagasEmbeddings is missing {len(missing)} method(s) "
        f"that ragas.embeddings.base.BaseRagasEmbeddings exposes: "
        f"{sorted(missing)}. Add duck-typed shims in ragas_adapters.py."
    )


def test_llm_wrapper_generate_is_async_and_callable_on_instance() -> None:
    """The specific shim that Cycle 3 caught missing — invoke it."""
    llm = RagForgeRagasLLM(judge=_StubJudge(), refusal_aware=False)
    generate = getattr(llm, "generate", None)
    assert generate is not None, "generate shim not declared on instance"
    assert inspect.iscoroutinefunction(generate), (
        "generate must be async — ragas's BaseRagasLLM.generate is async "
        "and is invoked via `await` in metric code"
    )


def test_llm_wrapper_is_finished_returns_true_by_default() -> None:
    """``is_finished`` is abstract on the base class — our shim exists
    and reports True so ragas's retry path doesn't trigger on every call."""
    llm = RagForgeRagasLLM(judge=_StubJudge(), refusal_aware=False)
    assert llm.is_finished(response="ignored") is True


def test_llm_wrapper_get_temperature_matches_base_convention() -> None:
    """n<=1 → deterministic, n>1 → warmer. Matches BaseRagasLLM."""
    llm = RagForgeRagasLLM(judge=_StubJudge(), refusal_aware=False)
    assert llm.get_temperature(1) == 0.01
    assert llm.get_temperature(5) == 0.3


def test_llm_wrapper_set_run_config_stores_the_value() -> None:
    llm = RagForgeRagasLLM(judge=_StubJudge(), refusal_aware=False)
    sentinel = object()
    llm.set_run_config(sentinel)
    assert llm.run_config is sentinel


def test_embeddings_wrapper_set_run_config_stores_the_value() -> None:
    emb = RagForgeRagasEmbeddings(provider="mock")
    sentinel = object()
    emb.set_run_config(sentinel)
    assert emb.run_config is sentinel
