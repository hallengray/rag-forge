"""Hallucination metric: what percentage of claims lack source support?"""
import logging

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.response_parser import parse_judge_json

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
        raw = judge.judge(_SYSTEM_PROMPT, user_prompt)
        outcome = parse_judge_json(raw)
        if not outcome.ok or outcome.data is None:
            logger.warning("Hallucination parse failed: %s", outcome.error)
            return MetricResult(
                name="hallucination",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details=f"judge response unparseable: {outcome.error}",
                skipped=True,
            )
        if "hallucination_rate" not in outcome.data:
            logger.warning("Hallucination: judge response missing 'hallucination_rate' field")
            return MetricResult(
                name="hallucination",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details="judge response missing 'hallucination_rate' field",
                skipped=True,
            )
        try:
            hallucination_rate = float(outcome.data["hallucination_rate"])
        except (TypeError, ValueError) as e:
            logger.warning("Hallucination: 'hallucination_rate' is not a number: %s", e)
            return MetricResult(
                name="hallucination",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details=f"'hallucination_rate' not numeric: {e}",
                skipped=True,
            )
        score = 1.0 - hallucination_rate
        return MetricResult(
            name="hallucination",
            score=score,
            threshold=self.default_threshold(),
            passed=score >= self.default_threshold(),
        )
