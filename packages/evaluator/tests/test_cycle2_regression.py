"""Regression test for the Cycle 2 failure signatures.

Asserts that running ragas against a sanitized 3-sample excerpt does
NOT reproduce any of the v0.1.3 pathologies:

  - AttributeError: 'OpenAIEmbeddings' object has no attribute 'embed_query'
    (Finding #4 — fixed by RagForgeRagasEmbeddings injection)
  - InstructorRetryException from max_tokens overflow on long clinical responses
    (Finding #5 — fixed by our LLM wrapper with configurable max_tokens)
  - Overall 0.0000 with all metrics at 0.0 and Skipped=0
    (Finding #6 — fixed by replacing the 0.0 fallback with SkipRecord tracking)

Gated by @pytest.mark.ragas_integration — skipped unless explicitly
requested with `pytest -m ragas_integration`. Also wrapped in
pytest.importorskip so it's a no-op when ragas is not installed.

Fixture notes:
  - Responses are synthesized to match clinical-structural complexity
    of actual Cycle 2 run (20-50 extractable statements per response)
    to trigger the max_tokens overflow if the bug reappeared.
  - Sample locations and identifiers are sanitized (test_location, etc.)
  - All three samples exercise distinct failure modes:
    * acs-001: baseline signal (good faithfulness, no errors)
    * htn-001: the faithfulness drift case (Finding #1 in audit notes)
    * t2dm-002: the safety guardrail refusal path (adversarial)
"""

import json
from pathlib import Path

import pytest

pytest.importorskip("ragas")

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.engines.ragas_evaluator import RagasEvaluator
from rag_forge_evaluator.judge.mock_judge import MockJudge

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ragas_regression" / "cycle-2-excerpt.jsonl"


def _load_samples() -> list[EvaluationSample]:
    """Load sanitized samples from the JSONL fixture."""
    samples: list[EvaluationSample] = []
    for line in FIXTURE_PATH.read_text().splitlines():
        if not line.strip() or line.strip().startswith("//"):
            continue
        row = json.loads(line)
        samples.append(
            EvaluationSample(
                query=row["query"],
                contexts=row["contexts"],
                response=row["response"],
                expected_answer=row.get("expected_answer", ""),
                sample_id=row["sample_id"],
            )
        )
    return samples


@pytest.mark.ragas_integration
def test_cycle2_fixture_does_not_reproduce_v013_failures():
    """Regression: confirm v0.1.3 pathologies are not reintroduced.

    The three pathologies we're guarding against:
      1. OpenAIEmbeddings.embed_query AttributeError (Finding #4)
      2. InstructorRetryException on max_tokens overflow (Finding #5)
      3. Silent 0.0 coercion without SkipRecord (Finding #6)

    If any of these reappear, this test will raise an exception (for #1, #2)
    or fail the assertion (for #3). On machines without ragas installed,
    pytest.importorskip at module scope will skip the entire test module.
    """
    samples = _load_samples()
    assert len(samples) >= 3, "fixture must contain at least 3 samples"

    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={},
        embeddings_provider="mock",
    )
    result = evaluator.evaluate(samples)

    # v0.1.3 signature: all metrics at 0.0 AND no skip records
    # (i.e., the silent 0.0 coercion bug). Either non-zero metrics OR
    # explicit skips are acceptable.
    all_zero = all(m.score == 0.0 for m in result.metrics) if result.metrics else True
    has_explanation = len(result.skipped_samples) > 0 or result.overall_score > 0.0

    assert not all_zero or has_explanation, (
        "v0.1.3 regression: all metrics zeroed with no SkipRecord explanation. "
        "Either the extractor silently coerced exceptions to 0.0, or ragas actually "
        "scored everything as zero without us noticing."
    )


@pytest.mark.ragas_integration
def test_cycle2_fixture_exceptions_produce_skip_records_not_silent_zeros():
    """Sanity check: exceptions → SkipRecord, not silent 0.0.

    Finding #6 of the audit notes documents that RAGAS exceptions were
    being coerced to 0.0 and marked as "scored" instead of "skipped".
    This test confirms that any metric scoring to 0.0 now has a corresponding
    SkipRecord explaining why.
    """
    samples = _load_samples()
    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={},
        embeddings_provider="mock",
    )
    result = evaluator.evaluate(samples)

    # If there are ANY metrics at 0.0 score, there must be a matching skip record
    for metric in result.metrics:
        if metric.score == 0.0:
            assert len(result.skipped_samples) > 0, (
                f"metric {metric.name} scored 0.0 with no skipped_samples — "
                "this is the v0.1.3 silent-coercion pathology"
            )


@pytest.mark.ragas_integration
def test_cycle2_fixture_no_openaiembeddings_attribute_error():
    """Regression: Finding #4 — OpenAIEmbeddings.embed_query AttributeError.

    This exception was observed 2x in the Cycle 2 RAGAS run.
    v0.2.0 fixes it by injecting RagForgeRagasEmbeddings (which handles
    the ragas 0.4.x API change internally). If this attribute error
    reappears, the test will raise and fail.

    **v0.2.2 update:** the assertion is no longer "metrics must be
    populated." With the G3 skip-counter fan-out, a run against MockJudge
    legitimately produces zero scored metrics and a full set of skip
    records explaining why (MockJudge can't answer ragas's prompts). The
    regression we're guarding against is specifically an AttributeError
    referencing ``OpenAIEmbeddings`` or ``embed_query`` — so we assert
    the call completed AND no skip record names that signature.
    """
    samples = _load_samples()
    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={},
        embeddings_provider="mock",
    )
    # If RagasEvaluator.evaluate() encounters an AttributeError during
    # embedding computation, our whole-batch catch swallows it into
    # skipped_samples. Inspect the skip records for the Finding #4
    # signature instead of relying on re-raise behaviour.
    result = evaluator.evaluate(samples)

    assert result is not None
    for skip in result.skipped_samples:
        reason_lower = skip.reason.lower()
        assert "openaiembeddings" not in reason_lower, (
            f"Finding #4 regression: skip reason names OpenAIEmbeddings "
            f"— {skip!r}"
        )
        assert "embed_query" not in reason_lower or "attributeerror" not in skip.exception_type.lower(), (
            f"Finding #4 regression: AttributeError on embed_query — {skip!r}"
        )


@pytest.mark.ragas_integration
def test_cycle2_fixture_handles_long_structured_responses():
    """Regression: Finding #5 — max_tokens overflow on long clinical responses.

    the cycle-2 customer's structured responses (conditions, triage, differential diagnoses,
    etc.) produce 20-50 extractable statements per case. Cycle 2 observed
    4x finish_reason='length' and 3x InstructorRetryException at the old max_tokens
    limit. v0.2.0 increases max_tokens and wraps the LLM with RagForgeRagasLLM
    which can configure it independently from ragas's defaults.

    The test fixture responses are long and structured to replicate the
    token pressure from the real audit. If the overflow bug reappears,
    either an exception will be raised or metrics will degrade to 0.0.
    """
    samples = _load_samples()

    # Ensure responses are actually long enough to trigger the issue if present
    for sample in samples:
        assert len(sample.response.split()) > 50, (
            f"Sample {sample.sample_id}: response too short to trigger Finding #5 "
            "(should have 50+ words to produce 20+ extractable statements)"
        )

    evaluator = RagasEvaluator(
        judge=MockJudge(),
        thresholds={},
        embeddings_provider="mock",
    )
    result = evaluator.evaluate(samples)

    # If we succeeded without InstructorRetryException, the fix holds.
    assert result is not None

    # **v0.2.2 update:** the original assertion demanded non-zero metrics.
    # With the G3 skip-counter fan-out, a MockJudge run legitimately
    # skips every metric (MockJudge can't answer ragas's prompts) and
    # the result comes back with ``metrics=[]`` and a full skip list.
    # The Cycle 2 Finding #5 regression we care about is specifically
    # InstructorRetryException / finish_reason='length' — assert those
    # signatures do NOT appear in any skip reason.
    for skip in result.skipped_samples:
        assert "InstructorRetryException" not in skip.exception_type, (
            f"Finding #5 regression: InstructorRetryException in skip — {skip!r}"
        )
        reason_lower = skip.reason.lower()
        assert "finish_reason='length'" not in reason_lower, (
            f"Finding #5 regression: max_tokens truncation in skip — {skip!r}"
        )

    # Also verify the old silent-coercion pathology: if any metric did
    # score (non-skip path), it must not silently be 0.0 with no
    # explanation. Either we have explicit skips OR real scores.
    real_metrics_scored = [m for m in result.metrics if not m.skipped]
    if real_metrics_scored and all(m.score == 0.0 for m in real_metrics_scored):
        assert result.skipped_samples, (
            "All scored metrics are 0.0 and there are no skip records "
            "explaining why — the Cycle 2 silent-coercion pathology."
        )
