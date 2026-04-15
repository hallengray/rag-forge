"""Tests for the v0.2.2 RAGAS skip counter plumbing (G3).

Cycle 3's PearMedica audit (2026-04-15) documented two residual
problems in v0.2.1's skip handling, separate from the C3-2
AttributeError that was the headline bug:

  1. When ragas's job loop crashes and every metric fails to score,
     the ``EvaluationResult.skipped_evaluations`` integer counter was
     never set. The detail list (``skipped_samples``) held real skip
     records, but the integer counter — which the report's top-level
     "Skipped: N" line consumes — stayed at 0. A user reading only the
     TL;DR would see "Scored: 0, Skipped: 0, success: true" and think
     nothing had happened, when in reality every job had crashed.

  2. Skip records were attributed at the *aggregate* level
     (``sample_id="<aggregate>"``, one record per metric name) instead
     of fanning out per (sample, metric) pair. A 12-sample x 4-metric
     run that failed entirely produced 4 skip records instead of 48,
     so the blast radius was under-reported by 12x.

This file is the regression guard for both. Skipped if the ``[ragas]``
extra is not installed.
"""

from __future__ import annotations

import pytest

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.engines.ragas_evaluator import RagasEvaluator
from rag_forge_evaluator.judge.mock_judge import MockJudge

pytestmark = pytest.mark.ragas_integration


def _make_samples(count: int) -> list[EvaluationSample]:
    return [
        EvaluationSample(
            query=f"question {i}?",
            contexts=[f"context chunk {i}"],
            response=f"answer {i}",
            expected_answer=f"expected {i}",
            sample_id=f"sample-{i:02d}",
        )
        for i in range(count)
    ]


def test_skipped_evaluations_counter_matches_skip_record_length() -> None:
    """``EvaluationResult.skipped_evaluations`` must equal
    ``len(skipped_samples)``. Cycle 3's "Skipped: 0 is still wrong"
    finding was precisely the two fields drifting apart — the integer
    counter reading 0 while the detail list held real records.
    """
    pytest.importorskip("ragas")

    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={},
        embeddings_provider="mock",
    )
    samples = _make_samples(3)
    result = evaluator.evaluate(samples)

    assert result.skipped_evaluations == len(result.skipped_samples), (
        f"skipped_evaluations counter ({result.skipped_evaluations}) "
        f"diverged from skipped_samples detail list length "
        f"({len(result.skipped_samples)}). The two must be kept in "
        f"lockstep so the report's top-level counter matches the "
        f"detail section."
    )


def test_whole_batch_crash_fans_out_to_every_sample_metric_pair() -> None:
    """A whole-batch ragas crash must produce one SkipRecord per
    (sample, metric) pair, not one per metric name. Cycle 3 reported
    4 aggregate skip records for a run that should have had 48.
    """
    pytest.importorskip("ragas")

    # Construct an evaluator that will trigger the whole-batch catch
    # path: we patch the ragas import at call time to force an
    # exception before ragas_evaluate() ever runs.
    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={},
        embeddings_provider="mock",
    )
    samples = _make_samples(3)

    # Monkeypatch the bound method to inject a synthetic whole-batch
    # failure. This is the exact code path the Cycle 3 AttributeError
    # took before v0.2.2 G1 fixed the generate() shim.
    import rag_forge_evaluator.engines.ragas_evaluator as mod

    real_import = mod.__dict__.copy()

    def _boom(*args: object, **kwargs: object) -> None:
        _ = args, kwargs
        raise RuntimeError("synthetic whole-batch ragas failure")

    # Patch ragas_evaluate inside the deferred import block.
    import ragas

    original_evaluate = ragas.evaluate
    ragas.evaluate = _boom  # type: ignore[assignment]
    try:
        result = evaluator.evaluate(samples)
    finally:
        ragas.evaluate = original_evaluate  # type: ignore[assignment]
        _ = real_import

    # 3 samples x 4 metrics = 12 skip records, not 4.
    expected = len(samples) * 4  # 4 metric names in RagasEvaluator
    assert len(result.skipped_samples) == expected, (
        f"expected {expected} skip records (3 samples x 4 metrics), "
        f"got {len(result.skipped_samples)}. Whole-batch failures must "
        f"fan out to every (sample, metric) pair."
    )
    assert result.skipped_evaluations == expected, (
        f"skipped_evaluations counter should equal the fan-out size "
        f"({expected}), got {result.skipped_evaluations}"
    )

    # Every skip record should name a real sample_id (not "<aggregate>")
    # so post-hoc analysis in the report can attribute failures to
    # specific samples.
    real_sample_ids = {s.sample_id for s in samples}
    for skip in result.skipped_samples:
        assert skip.sample_id in real_sample_ids, (
            f"skip record has sample_id={skip.sample_id!r} which is not "
            f"one of the real sample IDs {real_sample_ids!r} — aggregate "
            f"attribution has regressed"
        )
        assert skip.exception_type == "RuntimeError"
        assert "synthetic whole-batch" in skip.reason


def test_skip_reason_truncated_to_400_chars() -> None:
    """Long Python tracebacks must be truncated to prevent HTML / PDF
    rendering blowing up. The limit is 400 chars with a trailing '...'.
    """
    pytest.importorskip("ragas")

    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={},
        embeddings_provider="mock",
    )
    samples = _make_samples(1)

    # Synthetic exception with a very long message.
    import ragas

    long_message = "x" * 5000
    original_evaluate = ragas.evaluate

    def _boom(*args: object, **kwargs: object) -> None:
        _ = args, kwargs
        raise ValueError(long_message)

    ragas.evaluate = _boom  # type: ignore[assignment]
    try:
        result = evaluator.evaluate(samples)
    finally:
        ragas.evaluate = original_evaluate  # type: ignore[assignment]

    for skip in result.skipped_samples:
        assert len(skip.reason) <= 400, (
            f"skip reason longer than 400 chars: {len(skip.reason)}"
        )
        assert skip.reason.endswith("..."), (
            "long reasons should end with ellipsis to indicate truncation"
        )
