"""Faithfulness metric: is the response grounded in retrieved contexts?"""
import json
import logging

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert evaluator assessing whether a response is grounded in the provided context.

Identify every factual claim in the response. For each claim, determine if it is supported by the context.

Respond with ONLY valid JSON in this exact format:
{"claims": [{"text": "<claim>", "supported": true}], "score": 0.9}

The score should be the proportion of claims that are supported (0.0 to 1.0).
If there are no claims, return {"claims": [], "score": 1.0}."""


class FaithfulnessMetric:
    def name(self) -> str:
        return "faithfulness"

    def default_threshold(self) -> float:
        return 0.85

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        user_prompt = (
            f"Query: {sample.query}\n\n"
            f"Context:\n{chr(10).join(sample.contexts)}\n\n"
            f"Response: {sample.response}"
        )
        try:
            raw = judge.judge(_SYSTEM_PROMPT, user_prompt)
            data = json.loads(raw)
            score = float(data.get("score", 0.0))
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Faithfulness eval failed: %s", e)
            return MetricResult(
                name="faithfulness",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details=f"Judge returned invalid response: {e}",
            )
        return MetricResult(
            name="faithfulness",
            score=score,
            threshold=self.default_threshold(),
            passed=score >= self.default_threshold(),
        )
