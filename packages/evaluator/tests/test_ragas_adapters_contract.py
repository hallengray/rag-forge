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


def test_llm_wrapper_async_signature_matches_base(ragas_base_llm: type) -> None:
    """For every method that is ``async`` on ``BaseRagasLLM``, our
    wrapper's method of the same name must also be ``async`` — and vice
    versa. CodeRabbit on PR #36 pointed out that checking names alone
    lets sync-vs-async mismatches through. A sync wrapper of an async
    base method crashes at runtime the moment ragas invokes it with
    ``await``; a sync base method called with ``await`` crashes the
    other direction.
    """
    for name in _public_methods(ragas_base_llm):
        wrapper_attr = getattr(RagForgeRagasLLM, name, None)
        if wrapper_attr is None:
            continue  # name-parity test above catches missing methods
        base_is_async = inspect.iscoroutinefunction(getattr(ragas_base_llm, name))
        wrapper_is_async = inspect.iscoroutinefunction(wrapper_attr)
        assert wrapper_is_async == base_is_async, (
            f"RagForgeRagasLLM.{name} is "
            f"{'async' if wrapper_is_async else 'sync'} but "
            f"BaseRagasLLM.{name} is "
            f"{'async' if base_is_async else 'sync'}. Fix one to match."
        )


def test_embeddings_wrapper_async_signature_matches_base(
    ragas_base_embeddings: type,
) -> None:
    """Same async/sync parity check as the LLM wrapper, for embeddings.

    This is the test that would have caught v0.2.2's first attempt at
    sync ``embed_text`` / ``embed_texts`` before they shipped — both
    are ``async`` on ragas's ``BaseRagasEmbeddings`` in 0.4.x.
    """
    for name in _public_methods(ragas_base_embeddings):
        wrapper_attr = getattr(RagForgeRagasEmbeddings, name, None)
        if wrapper_attr is None:
            continue
        base_is_async = inspect.iscoroutinefunction(
            getattr(ragas_base_embeddings, name)
        )
        wrapper_is_async = inspect.iscoroutinefunction(wrapper_attr)
        assert wrapper_is_async == base_is_async, (
            f"RagForgeRagasEmbeddings.{name} is "
            f"{'async' if wrapper_is_async else 'sync'} but "
            f"BaseRagasEmbeddings.{name} is "
            f"{'async' if base_is_async else 'sync'}. Fix one to match."
        )


def _required_param_names(cls: type, method_name: str) -> set[str]:
    """Return the set of named parameters on ``cls.method_name``.

    Excludes ``self`` / ``cls`` and variadic ``*args`` / ``**kwargs``
    catchalls. Used by the parameter-parity tests below to compare
    the named parameters a wrapper accepts against what the base
    class declares. Extra parameters on the wrapper are fine;
    missing parameters mean ragas will hit a ``TypeError`` the
    moment it passes that kwarg.
    """
    try:
        sig = inspect.signature(getattr(cls, method_name))
    except (ValueError, TypeError):
        return set()
    return {
        name
        for name, param in sig.parameters.items()
        if name not in ("self", "cls")
        and param.kind
        not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    }


def test_llm_wrapper_parameter_names_cover_base_class(
    ragas_base_llm: type,
) -> None:
    """For every method present on both the base class and our wrapper,
    the wrapper must accept at least every named parameter the base
    class declares. Missing a name means ragas will hit a TypeError
    the moment it tries to pass that kwarg.

    CodeRabbit on PR #38 round 2 pointed out that checking async/sync
    parity alone lets parameter drift through. A future ragas release
    that adds ``max_tokens`` to ``generate_text`` would silently break
    our wrapper until a user audit caught it.
    """
    for name in _public_methods(ragas_base_llm):
        if getattr(RagForgeRagasLLM, name, None) is None:
            continue
        base_params = _required_param_names(ragas_base_llm, name)
        wrapper_params = _required_param_names(RagForgeRagasLLM, name)
        missing = base_params - wrapper_params
        assert not missing, (
            f"RagForgeRagasLLM.{name} is missing parameters that "
            f"BaseRagasLLM.{name} declares: {sorted(missing)}. Either "
            f"add them to the shim signature or accept **kwargs so "
            f"ragas's caller can still pass them."
        )


def test_embeddings_wrapper_parameter_names_cover_base_class(
    ragas_base_embeddings: type,
) -> None:
    """Same parameter-parity check for the embeddings wrapper."""
    for name in _public_methods(ragas_base_embeddings):
        if getattr(RagForgeRagasEmbeddings, name, None) is None:
            continue
        base_params = _required_param_names(ragas_base_embeddings, name)
        wrapper_params = _required_param_names(RagForgeRagasEmbeddings, name)
        missing = base_params - wrapper_params
        assert not missing, (
            f"RagForgeRagasEmbeddings.{name} is missing parameters "
            f"that BaseRagasEmbeddings.{name} declares: {sorted(missing)}."
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
