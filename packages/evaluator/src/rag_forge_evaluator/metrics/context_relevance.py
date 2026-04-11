"""Context relevance metric: are the retrieved chunks relevant to the query?"""
import json
import logging

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert evaluator assessing whether retrieved context chunks are relevant to a query.

Rate each context chunk's relevance to the query on a 1-5 scale.

Respond with ONLY valid JSON in this exact format:
{"ratings": [{"chunk_index": 0, "score": 4, "reason": "brief reason"}], "mean_score": 0.8}

The mean_score should be the average rating divided by 5 (normalized to 0.0-1.0)."""


class ContextRelevanceMetric:
    def name(self) -> str:
        return "context_relevance"

    def default_threshold(self) -> float:
        return 0.80

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        chunks_text = "\n\n".join(
            f"[Chunk {i}]: {ctx}" for i, ctx in enumerate(sample.contexts)
        )
        user_prompt = f"Query: {sample.query}\n\nContext chunks:\n{chunks_text}"
        try:
            raw = judge.judge(_SYSTEM_PROMPT, user_prompt)
            data = json.loads(raw)
            score = float(data.get("mean_score", 0.0))
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Context relevance eval failed: %s", e)
            return MetricResult(
                name="context_relevance",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details=f"Judge returned invalid response: {e}",
            )
        return MetricResult(
            name="context_relevance",
            score=score,
            threshold=self.default_threshold(),
            passed=score >= self.default_threshold(),
        )
