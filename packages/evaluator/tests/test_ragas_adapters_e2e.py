"""End-to-end smoke test: run ``ragas.evaluate()`` against our wrappers.

This is the test that would have caught the v0.2.1 C3-2 regression before
publish. It invokes ragas's own evaluation entrypoint on a tiny two-sample
dataset, passing ``RagForgeRagasLLM`` and ``RagForgeRagasEmbeddings`` as
the ``llm`` and ``embeddings`` arguments — the exact call path that
crashed with ``AttributeError: no attribute 'generate'`` on every metric
job during the PearMedica Cycle 3 audit.

If this test passes, the wrappers implement enough of the ragas contract
for a real ``evaluate()`` call to complete. If it fails, something in
ragas's async job loop reached into an undeclared method — repeat the
contract-test audit, add the missing shim, re-run.

Skipped gracefully if the ``[ragas]`` extra is not installed.
"""

from __future__ import annotations

import os
from typing import Any

import pytest


class _DeterministicJudge:
    """Judge stub that returns canned JSON responses ragas can parse.

    ragas's faithfulness metric goes through two stages:
      1. Ask the LLM to extract a list of "statements" from the answer.
      2. For each statement, ask the LLM to verdict it against the context.

    A smoke-test judge just needs to return valid-looking JSON in both
    stages — we never try to measure actual quality here, only to prove
    the wrapper's dispatch and return shape are compatible with ragas's
    internal plumbing.
    """

    def __init__(self) -> None:
        self.call_count = 0

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        _ = system_prompt
        self.call_count += 1
        text = user_prompt.lower()
        # Statement-extraction stage
        if "statement" in text and "extract" in text:
            return '{"statements": ["Paris is the capital of France."]}'
        # Per-statement verdict stage
        if "verdict" in text or "faithful" in text:
            return (
                '{"statements": [{"statement": "Paris is the capital of France.", '
                '"verdict": 1, "reason": "directly stated in context"}]}'
            )
        # Fallback — some metrics emit a generic prompt
        return '{"answer": "Paris", "score": 1}'

    def model_name(self) -> str:
        return "deterministic-judge-stub"


def _make_dataset() -> Any:
    datasets = pytest.importorskip("datasets")
    return datasets.Dataset.from_dict(
        {
            "question": ["What is the capital of France?"],
            "answer": ["Paris is the capital of France."],
            "contexts": [["Paris is the capital city of France."]],
            "ground_truth": ["Paris"],
        }
    )


def test_ragas_evaluate_never_raises_attribute_error_on_wrapper() -> None:
    """Invoke ragas.evaluate() with our wrappers on a 1-sample dataset.

    **What this test is proving, and what it is NOT proving.**

    Proving: ragas's async job loop can reach our ``RagForgeRagasLLM``
    and ``RagForgeRagasEmbeddings`` instances and call every method
    they need without hitting an ``AttributeError``. This is the exact
    failure mode the PearMedica Cycle 3 audit caught in v0.2.1:
    ``AttributeError: 'RagForgeRagasLLM' object has no attribute 'generate'``
    — every metric job crashed identically before any real evaluation
    logic ran.

    NOT proving: that the metric produces a meaningful score, or that
    the output parser accepts our stub judge's return values. A stub
    judge returning canned JSON cannot match every pydantic schema
    ragas uses internally across versions — fighting that is a losing
    game for a smoke test. If the call fails with
    ``RagasOutputParserException`` or similar parser errors, the
    wrapper dispatch worked and ragas is doing its own thing downstream.
    We assert on exception **type** rather than demanding a clean
    return.

    Run against real production telemetry (not a stub) when verifying
    end-to-end evaluation quality — see the Cycle 3 RAGAS re-run
    planned for Workstream G2.
    """
    pytest.importorskip("ragas")
    pytest.importorskip("langchain_core")
    pytest.importorskip("datasets")

    from ragas import evaluate
    from ragas.metrics import faithfulness

    from rag_forge_evaluator.engines.ragas_adapters import (
        RagForgeRagasEmbeddings,
        RagForgeRagasLLM,
    )

    os.environ.setdefault("OPENAI_API_KEY", "sk-test-nonce")

    llm = RagForgeRagasLLM(judge=_DeterministicJudge(), refusal_aware=False)
    embeddings = RagForgeRagasEmbeddings(provider="mock")
    dataset = _make_dataset()

    # What we expect downstream of our wrappers when everything is
    # shaped correctly: ragas's faithfulness metric reaches its
    # pydantic output parser and fails to parse our stub judge's
    # canned JSON. That raises a ragas-internal exception (either
    # ``RagasOutputParserException`` or a ``RagasException``
    # subclass). **Any other exception shape** — TypeError from a bad
    # shim signature, RuntimeError from a nested-loop bug, ValueError
    # from embedding dimension mismatch — means something our wrapper
    # is responsible for went wrong, and the test must fail.
    #
    # CodeRabbit on PR #36 pointed out the original broad
    # ``except Exception`` swallowed real bugs as long as they
    # weren't AttributeError. This tightening makes the regression
    # guard meaningful.
    allowed_exception_types: tuple[type[BaseException], ...]
    try:
        from ragas.exceptions import RagasOutputParserException  # type: ignore[attr-defined]

        allowed_exception_types = (RagasOutputParserException,)
    except ImportError:
        allowed_exception_types = ()

    try:
        evaluate(
            dataset=dataset,
            metrics=[faithfulness],
            llm=llm,
            embeddings=embeddings,
            raise_exceptions=True,
            show_progress=False,
        )
    except AttributeError as exc:
        wrapper_names = ("RagForgeRagasLLM", "RagForgeRagasEmbeddings")
        if any(name in str(exc) for name in wrapper_names):
            pytest.fail(
                f"ragas called a method on our wrapper that doesn't "
                f"exist: {exc!r}. Add the missing shim in "
                f"ragas_adapters.py and update the contract test."
            )
        raise
    except allowed_exception_types:
        # Parser / schema failure downstream of our wrappers. The
        # wrapper dispatch worked; ragas is now doing its own thing
        # with a stub judge that returns JSON not matching its
        # internal pydantic schemas. Treat as success.
        pass
