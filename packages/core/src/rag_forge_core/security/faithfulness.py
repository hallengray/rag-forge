"""Faithfulness checking via LLM-as-judge."""

import json
import logging
from dataclasses import dataclass

from rag_forge_core.generation.base import GenerationProvider

logger = logging.getLogger(__name__)

_FAITHFULNESS_SYSTEM_PROMPT = (
    "You are a faithfulness evaluator. Determine whether the response "
    "is fully grounded in the provided context. Score from 0.0 (completely "
    "unfaithful) to 1.0 (fully grounded).\n\n"
    'Respond with ONLY a JSON object: {"score": 0.0-1.0, "reason": "brief explanation"}'
)


@dataclass
class FaithfulnessResult:
    passed: bool
    score: float
    threshold: float
    reason: str | None = None


class FaithfulnessChecker:
    def __init__(self, generator: GenerationProvider, threshold: float = 0.85) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        self._generator = generator
        self._threshold = threshold

    def check(self, response: str, contexts: list[str]) -> FaithfulnessResult:
        if not contexts:
            return FaithfulnessResult(
                passed=True, score=1.0, threshold=self._threshold, reason="No contexts to check against"
            )

        context_text = "\n\n".join(contexts)
        user_prompt = f"Context:\n{context_text}\n\nResponse:\n{response}"

        try:
            llm_response = self._generator.generate(_FAITHFULNESS_SYSTEM_PROMPT, user_prompt)
            parsed = json.loads(llm_response)
            score = float(parsed.get("score", 1.0))
            reason = parsed.get("reason")
            return FaithfulnessResult(
                passed=score >= self._threshold,
                score=score,
                threshold=self._threshold,
                reason=reason,
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logger.warning(
                "Faithfulness checker returned malformed response, blocking for safety", exc_info=True
            )
            return FaithfulnessResult(
                passed=False,
                score=0.0,
                threshold=self._threshold,
                reason="Checker returned malformed response — blocking for safety",
            )
        except Exception:
            logger.warning("Faithfulness check failed, blocking for safety", exc_info=True)
            return FaithfulnessResult(
                passed=False,
                score=0.0,
                threshold=self._threshold,
                reason="Faithfulness check failed — blocking for safety",
            )
