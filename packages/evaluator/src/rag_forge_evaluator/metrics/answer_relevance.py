"""Answer relevance metric: does the response address the question asked?"""
import logging

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.response_parser import parse_judge_json

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert evaluator assessing whether a response adequately addresses the question asked.

Score the response on three dimensions (each 1-5):
- completeness: Does it address all parts of the query?
- correctness: Are the facts accurate?
- coherence: Is it well-structured and clear?

Respond with ONLY valid JSON in this exact format:
{"completeness": 4, "correctness": 5, "coherence": 4, "overall_score": 0.87}

The overall_score should be the mean of all three scores divided by 5 (normalized to 0.0-1.0)."""


class AnswerRelevanceMetric:
    def name(self) -> str:
        return "answer_relevance"

    def default_threshold(self) -> float:
        return 0.80

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        user_prompt = f"Query: {sample.query}\n\nResponse: {sample.response}"
        raw = judge.judge(_SYSTEM_PROMPT, user_prompt)
        outcome = parse_judge_json(raw)
        if not outcome.ok or outcome.data is None:
            logger.warning("Answer relevance parse failed: %s", outcome.error)
            return MetricResult(
                name="answer_relevance",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details=f"judge response unparseable: {outcome.error}",
                skipped=True,
            )
        if "overall_score" not in outcome.data:
            logger.warning("Answer relevance: judge response missing 'overall_score' field")
            return MetricResult(
                name="answer_relevance",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details="judge response missing 'overall_score' field",
                skipped=True,
            )
        try:
            score = float(outcome.data["overall_score"])
        except (TypeError, ValueError) as e:
            logger.warning("Answer relevance: 'overall_score' is not a number: %s", e)
            return MetricResult(
                name="answer_relevance",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details=f"'overall_score' not numeric: {e}",
                skipped=True,
            )
        return MetricResult(
            name="answer_relevance",
            score=score,
            threshold=self.default_threshold(),
            passed=score >= self.default_threshold(),
        )
