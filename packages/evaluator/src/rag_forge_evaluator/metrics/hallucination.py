"""Hallucination metric: what percentage of claims lack source support?"""
import json
import logging

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert evaluator detecting hallucinations in RAG pipeline responses.

Extract every factual claim from the response. For each claim, determine if it is supported by any of the provided context chunks.

Respond with ONLY valid JSON in this exact format:
{"claims": [{"text": "<claim>", "supported": true, "source_chunk": 0}], "unsupported_count": 0, "total_claims": 2, "hallucination_rate": 0.0}

hallucination_rate = unsupported_count / total_claims (0.0 to 1.0).
If there are no claims, return hallucination_rate: 0.0."""


class HallucinationMetric:
    def name(self) -> str:
        return "hallucination"

    def default_threshold(self) -> float:
        return 0.95

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        chunks_text = "\n\n".join(
            f"[Chunk {i}]: {ctx}" for i, ctx in enumerate(sample.contexts)
        )
        user_prompt = (
            f"Query: {sample.query}\n\n"
            f"Context chunks:\n{chunks_text}\n\n"
            f"Response: {sample.response}"
        )
        try:
            raw = judge.judge(_SYSTEM_PROMPT, user_prompt)
            data = json.loads(raw)
            hallucination_rate = float(data.get("hallucination_rate", 1.0))
            score = 1.0 - hallucination_rate
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Hallucination eval failed: %s", e)
            return MetricResult(
                name="hallucination",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details=f"Judge returned invalid response: {e}",
            )
        return MetricResult(
            name="hallucination",
            score=score,
            threshold=self.default_threshold(),
            passed=score >= self.default_threshold(),
        )
