"""Adversarial test runner for RAG pipeline security guards.

Runs a corpus of attack prompts against InputGuard and reports pass/fail rates.
Ships a built-in corpus and supports user extensions.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rag_forge_core.security.injection import PromptInjectionDetector
from rag_forge_core.security.input_guard import GuardResult, InputGuard
from rag_forge_core.security.pii import RegexPIIScanner

_CORPUS_PATH = Path(__file__).parent / "adversarial_corpus.json"


def load_corpus(user_corpus_path: str | None = None) -> list[dict[str, Any]]:
    """Load the built-in adversarial corpus, optionally merging user extensions."""
    with _CORPUS_PATH.open() as f:
        data = json.load(f)
    prompts = list(data["prompts"])

    if user_corpus_path:
        user_path = Path(user_corpus_path)
        if user_path.exists():
            with user_path.open() as f:
                user_data = json.load(f)
            prompts.extend(user_data.get("prompts", []))

    return prompts


@dataclass
class AdversarialResult:
    """Result of an adversarial test run."""

    total_tested: int
    blocked: int
    passed_through: int
    pass_rate: float
    by_category: dict[str, dict[str, Any]]
    failures: list[dict[str, Any]] = field(default_factory=list)


class AdversarialRunner:
    """Runs adversarial prompts against InputGuard and reports results."""

    def __init__(
        self,
        guard: InputGuard | None = None,
        user_corpus_path: str | None = None,
    ) -> None:
        self._guard = guard or InputGuard(
            injection_detector=PromptInjectionDetector(),
            pii_scanner=RegexPIIScanner(),
        )
        self._user_corpus_path = user_corpus_path

    def run(self) -> AdversarialResult:
        """Run all adversarial prompts and collect results."""
        prompts = load_corpus(self._user_corpus_path)

        categories: dict[str, dict[str, int]] = {}
        failures: list[dict[str, Any]] = []
        total_blocked = 0

        for prompt in prompts:
            text = prompt["text"]
            category = prompt["category"]
            expected_blocked = prompt["expected_blocked"]

            result: GuardResult = self._guard.check(text)
            was_blocked = not result.passed

            if category not in categories:
                categories[category] = {"tested": 0, "blocked": 0}
            categories[category]["tested"] += 1
            if was_blocked:
                categories[category]["blocked"] += 1
                total_blocked += 1

            if expected_blocked and not was_blocked:
                failures.append({
                    "text": text,
                    "category": category,
                    "severity": prompt.get("severity", "unknown"),
                    "expected_blocked": True,
                })

        total = len(prompts)
        passed_through = total - total_blocked

        by_category: dict[str, dict[str, Any]] = {}
        for cat, stats in categories.items():
            tested = stats["tested"]
            blocked = stats["blocked"]
            by_category[cat] = {
                "tested": tested,
                "blocked": blocked,
                "pass_rate": blocked / tested if tested > 0 else 0.0,
            }

        return AdversarialResult(
            total_tested=total,
            blocked=total_blocked,
            passed_through=passed_through,
            pass_rate=total_blocked / total if total > 0 else 0.0,
            by_category=by_category,
            failures=failures,
        )
