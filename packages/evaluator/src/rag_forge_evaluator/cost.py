"""Cost estimation for RAG pipelines.

Projects monthly spend based on token usage telemetry and model pricing.
PRD spec: `rag-forge cost --estimate` for monthly spend projection.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CostReport:
    """Result of a cost estimation."""

    daily_cost: float
    monthly_cost: float
    breakdown: list[dict[str, Any]]
    queries_per_day: int


class ModelPricing:
    """Pricing table for common LLM and embedding models.

    Prices are per 1K tokens. Users bring their own API keys,
    so we track public pricing for estimation only.
    """

    def __init__(self, models: dict[str, dict[str, float]]) -> None:
        self.models = models

    @classmethod
    def defaults(cls) -> "ModelPricing":
        """Default pricing as of early 2026. Costs per 1K tokens in USD."""
        return cls(
            models={
                "text-embedding-3-large": {"input": 0.00013, "output": 0.0},
                "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
                "gpt-4o": {"input": 0.0025, "output": 0.01},
                "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
                "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
                "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
                "rerank-v3.5": {"input": 0.002, "output": 0.0},
                "mock-embedder": {"input": 0.0, "output": 0.0},
                "mock-generator": {"input": 0.0, "output": 0.0},
            }
        )

    def cost_per_1k_input(self, model: str) -> float:
        if model in self.models:
            return self.models[model]["input"]
        return 0.0

    def cost_per_1k_output(self, model: str) -> float:
        if model in self.models:
            return self.models[model]["output"]
        return 0.0


class CostEstimator:
    """Estimates monthly RAG pipeline costs from token usage telemetry."""

    def __init__(self, pricing: ModelPricing | None = None) -> None:
        self.pricing = pricing or ModelPricing.defaults()

    def estimate(
        self,
        telemetry: list[dict[str, Any]],
        queries_per_day: int,
    ) -> CostReport:
        """Estimate costs from telemetry data.

        Args:
            telemetry: List of dicts with keys: model, input_tokens, output_tokens, calls.
            queries_per_day: Projected daily query volume.
        """
        if queries_per_day == 0 or not telemetry:
            return CostReport(
                daily_cost=0.0,
                monthly_cost=0.0,
                breakdown=[],
                queries_per_day=queries_per_day,
            )

        total_sample_calls = sum(entry.get("calls", 1) for entry in telemetry)
        if total_sample_calls == 0:
            total_sample_calls = 1

        breakdown: list[dict[str, Any]] = []
        total_cost_per_query = 0.0

        for entry in telemetry:
            model = entry["model"]
            input_tokens = entry.get("input_tokens", 0)
            output_tokens = entry.get("output_tokens", 0)
            calls = entry.get("calls", 1)

            input_cost = (input_tokens / 1000) * self.pricing.cost_per_1k_input(model)
            output_cost = (output_tokens / 1000) * self.pricing.cost_per_1k_output(model)
            sample_cost = input_cost + output_cost
            per_query = sample_cost / total_sample_calls if total_sample_calls > 0 else 0.0
            total_cost_per_query += per_query

            breakdown.append(
                {
                    "model": model,
                    "input_tokens_per_query": input_tokens / calls if calls > 0 else 0,
                    "output_tokens_per_query": output_tokens / calls if calls > 0 else 0,
                    "cost_per_query": per_query,
                }
            )

        daily = total_cost_per_query * queries_per_day
        monthly = daily * 30

        return CostReport(
            daily_cost=daily,
            monthly_cost=monthly,
            breakdown=breakdown,
            queries_per_day=queries_per_day,
        )
