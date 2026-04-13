"""Rough cost and duration estimates for audit runs.

These are ESTIMATES shown to the user before a run so they can make an
informed decision about whether to proceed. Actual cost depends on prompt
length, retry count, and provider pricing changes — we intentionally
over-estimate on both axes so the real bill comes in at or below the quote.

The pricing table is keyed by the judge model name. Unknown models fall
back to a conservative assumption (gpt-4o pricing) and are flagged as
estimated-only in the banner.
"""

from dataclasses import dataclass

# ($ per million input tokens, $ per million output tokens)
# Last updated: 2026-04-13 from public provider pricing pages.
_PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-opus-4-6": (15.0, 75.0),
    "claude-opus-4-6-1m": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # OpenAI
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-2024-11-20": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.0, 30.0),
    # Mock / local
    "mock": (0.0, 0.0),
    "mock-judge": (0.0, 0.0),
}

# Rough per-call token assumptions for a judge evaluation.
# Input  = system prompt + query + contexts + response (~1200-2000 tokens)
# Output = structured JSON enumeration of every claim in the response
#          (~400-1200 tokens for faithfulness/hallucination on long
#          responses, ~50-100 for answer_relevance/context_relevance).
#          800 is the weighted average across the four default metrics.
_AVG_INPUT_TOKENS = 1500
_AVG_OUTPUT_TOKENS = 800

# Rough per-call wall-clock seconds. The low end assumes happy-path streaming;
# the high end accounts for retries and upstream queueing.
_SECONDS_PER_CALL_LOW = 4.0
_SECONDS_PER_CALL_HIGH = 10.0


@dataclass(frozen=True)
class AuditEstimate:
    """Pre-run estimate shown to the user in the banner."""

    judge_calls: int
    judge_model: str
    cost_usd: float
    minutes_low: float
    minutes_high: float
    is_fallback_pricing: bool


def estimate_audit(
    *,
    sample_count: int,
    metric_count: int,
    judge_model: str,
) -> AuditEstimate:
    """Estimate cost and duration for an audit run.

    Args:
        sample_count: Number of samples to evaluate.
        metric_count: Number of metrics per sample (one judge call each).
        judge_model: Model name as it will be passed to the judge provider.

    Returns:
        An ``AuditEstimate`` with judge call count, USD cost, and a minute range.
    """
    judge_calls = sample_count * metric_count

    price = _PRICE_PER_MTOK.get(judge_model)
    is_fallback = price is None
    if price is None:
        price = _PRICE_PER_MTOK["gpt-4o"]

    in_price, out_price = price
    total_input_tokens = judge_calls * _AVG_INPUT_TOKENS
    total_output_tokens = judge_calls * _AVG_OUTPUT_TOKENS
    cost_usd = (total_input_tokens / 1_000_000) * in_price + (
        total_output_tokens / 1_000_000
    ) * out_price

    minutes_low = (judge_calls * _SECONDS_PER_CALL_LOW) / 60.0
    minutes_high = (judge_calls * _SECONDS_PER_CALL_HIGH) / 60.0

    return AuditEstimate(
        judge_calls=judge_calls,
        judge_model=judge_model,
        cost_usd=round(cost_usd, 2),
        minutes_low=round(minutes_low, 1),
        minutes_high=round(minutes_high, 1),
        is_fallback_pricing=is_fallback,
    )
