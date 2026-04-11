# Phase 1B: Evaluation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the evaluation pipeline so `rag-forge audit --input telemetry.jsonl` scores RAG output quality using LLM-as-Judge and produces an HTML audit report with RMM scoring.

**Architecture:** Metric-per-class with evaluator orchestrator. Each metric (faithfulness, context relevance, answer relevance, hallucination) is its own class behind a `MetricEvaluator` protocol. `LLMJudgeEvaluator` delegates to metrics via a `JudgeProvider` abstraction (Claude, GPT-4o, or mock). `AuditOrchestrator` coordinates the full pipeline: load input → evaluate → score RMM → generate HTML report.

**Tech Stack:** Python 3.11+ (pydantic, jinja2, anthropic, openai), TypeScript (Commander.js, execa), pytest, vitest.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/evaluator/src/rag_forge_evaluator/input_loader.py` | Load JSONL telemetry and golden set JSON into EvaluationSample lists |
| `packages/evaluator/src/rag_forge_evaluator/judge/base.py` | JudgeProvider protocol |
| `packages/evaluator/src/rag_forge_evaluator/judge/mock_judge.py` | Deterministic mock for testing |
| `packages/evaluator/src/rag_forge_evaluator/judge/claude_judge.py` | Claude via Anthropic SDK |
| `packages/evaluator/src/rag_forge_evaluator/judge/openai_judge.py` | GPT-4o via OpenAI SDK |
| `packages/evaluator/src/rag_forge_evaluator/judge/__init__.py` | Module exports |
| `packages/evaluator/src/rag_forge_evaluator/metrics/base.py` | MetricEvaluator protocol |
| `packages/evaluator/src/rag_forge_evaluator/metrics/faithfulness.py` | Faithfulness metric |
| `packages/evaluator/src/rag_forge_evaluator/metrics/context_relevance.py` | Context relevance metric |
| `packages/evaluator/src/rag_forge_evaluator/metrics/answer_relevance.py` | Answer relevance metric |
| `packages/evaluator/src/rag_forge_evaluator/metrics/hallucination.py` | Hallucination rate metric |
| `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py` | LLMJudgeEvaluator orchestrator |
| `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2` | Jinja2 HTML template |
| `packages/evaluator/src/rag_forge_evaluator/cli.py` | Python CLI entry point for TS bridge |
| `packages/evaluator/tests/test_input_loader.py` | Input loading tests |
| `packages/evaluator/tests/test_metrics.py` | Metric + judge tests |
| `packages/evaluator/tests/test_audit.py` | Audit orchestrator integration test |
| `packages/evaluator/tests/test_report.py` | Report generation tests |

### Modified Files

| File | Change |
|------|--------|
| `packages/evaluator/pyproject.toml` | Add anthropic, openai dependencies |
| `packages/evaluator/src/rag_forge_evaluator/golden_set.py` | Real JSON loading logic |
| `packages/evaluator/src/rag_forge_evaluator/maturity.py` | Real RMM assess() logic |
| `packages/evaluator/src/rag_forge_evaluator/audit.py` | Full orchestration + AuditReport dataclass |
| `packages/evaluator/src/rag_forge_evaluator/report/generator.py` | Jinja2 template rendering |
| `packages/cli/src/commands/audit.ts` | Wire to Python bridge |

---

## Task 1: Add Dependencies

**Files:**
- Modify: `packages/evaluator/pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

Replace `packages/evaluator/pyproject.toml` with:

```toml
[project]
name = "rag-forge-evaluator"
version = "0.1.0"
description = "Evaluation engine: RAGAS, DeepEval, LLM-as-Judge, and audit report generation"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "pydantic>=2.0",
    "jinja2>=3.1",
    "anthropic>=0.30",
    "openai>=1.30",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/rag_forge_evaluator"]
```

- [ ] **Step 2: Install dependencies**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv sync --all-packages`
Expected: anthropic and openai packages install successfully.

- [ ] **Step 3: Verify existing tests still pass**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/ -v`
Expected: 5 existing maturity tests pass.

- [ ] **Step 4: Commit**

```bash
git add packages/evaluator/pyproject.toml uv.lock
git commit -m "chore(evaluator): add anthropic and openai dependencies"
```

---

## Task 2: Input Loader (JSONL + Golden Set)

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/input_loader.py`
- Modify: `packages/evaluator/src/rag_forge_evaluator/golden_set.py`
- Create: `packages/evaluator/tests/test_input_loader.py`

- [ ] **Step 1: Write failing tests**

Create `packages/evaluator/tests/test_input_loader.py`:

```python
"""Tests for JSONL and golden set input loading."""

import json
from pathlib import Path

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.input_loader import InputLoader


class TestLoadJsonl:
    def test_loads_valid_jsonl(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "telemetry.jsonl"
        lines = [
            {"query": "What is Python?", "contexts": ["Python is a language."], "response": "Python is a programming language."},
            {"query": "What is Rust?", "contexts": ["Rust is fast."], "response": "Rust is a systems language."},
        ]
        jsonl.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
        samples = InputLoader.load_jsonl(jsonl)
        assert len(samples) == 2
        assert isinstance(samples[0], EvaluationSample)
        assert samples[0].query == "What is Python?"
        assert samples[0].contexts == ["Python is a language."]
        assert samples[0].response == "Python is a programming language."

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "bad.jsonl"
        jsonl.write_text(
            '{"query": "ok", "contexts": ["c"], "response": "r"}\n'
            'not valid json\n'
            '{"query": "also ok", "contexts": ["c2"], "response": "r2"}\n',
            encoding="utf-8",
        )
        samples = InputLoader.load_jsonl(jsonl)
        assert len(samples) == 2

    def test_skips_lines_missing_required_fields(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "partial.jsonl"
        jsonl.write_text(
            '{"query": "q", "contexts": ["c"], "response": "r"}\n'
            '{"query": "missing response", "contexts": ["c"]}\n',
            encoding="utf-8",
        )
        samples = InputLoader.load_jsonl(jsonl)
        assert len(samples) == 1

    def test_optional_fields_populated(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "full.jsonl"
        jsonl.write_text(
            json.dumps({
                "query": "q",
                "contexts": ["c"],
                "response": "r",
                "expected_answer": "expected",
                "chunk_ids": ["chunk_1"],
            }),
            encoding="utf-8",
        )
        samples = InputLoader.load_jsonl(jsonl)
        assert samples[0].expected_answer == "expected"
        assert samples[0].chunk_ids == ["chunk_1"]

    def test_empty_file(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "empty.jsonl"
        jsonl.write_text("", encoding="utf-8")
        assert InputLoader.load_jsonl(jsonl) == []


class TestLoadGoldenSet:
    def test_loads_golden_set(self, tmp_path: Path) -> None:
        gs = tmp_path / "golden.json"
        gs.write_text(
            json.dumps([
                {
                    "query": "What is RAG?",
                    "expected_answer_keywords": ["retrieval", "augmented"],
                    "difficulty": "easy",
                    "topic": "general",
                },
            ]),
            encoding="utf-8",
        )
        samples = InputLoader.load_golden_set(gs)
        assert len(samples) == 1
        assert samples[0].query == "What is RAG?"
        assert samples[0].expected_answer == "retrieval, augmented"
        assert samples[0].contexts == []
        assert samples[0].response == ""

    def test_empty_golden_set(self, tmp_path: Path) -> None:
        gs = tmp_path / "empty.json"
        gs.write_text("[]", encoding="utf-8")
        assert InputLoader.load_golden_set(gs) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_input_loader.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement InputLoader**

Create `packages/evaluator/src/rag_forge_evaluator/input_loader.py`:

```python
"""Load evaluation inputs from JSONL telemetry files or golden set JSON."""

import json
import logging
from pathlib import Path

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.golden_set import GoldenSetEntry

logger = logging.getLogger(__name__)

_REQUIRED_JSONL_FIELDS = {"query", "contexts", "response"}


class InputLoader:
    """Loads evaluation samples from JSONL or golden set files."""

    @staticmethod
    def load_jsonl(path: Path) -> list[EvaluationSample]:
        """Load samples from a JSONL telemetry file.

        Each line must be JSON with required fields: query, contexts, response.
        Malformed or incomplete lines are skipped with a warning.
        """
        samples: list[EvaluationSample] = []
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return samples

        for line_num, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON at line %d", line_num)
                continue

            if not isinstance(data, dict) or not _REQUIRED_JSONL_FIELDS.issubset(data.keys()):
                logger.warning("Skipping line %d: missing required fields", line_num)
                continue

            samples.append(
                EvaluationSample(
                    query=data["query"],
                    contexts=data["contexts"],
                    response=data["response"],
                    expected_answer=data.get("expected_answer"),
                    chunk_ids=data.get("chunk_ids"),
                )
            )
        return samples

    @staticmethod
    def load_golden_set(path: Path) -> list[EvaluationSample]:
        """Load samples from a golden set JSON file.

        Golden set entries are converted to EvaluationSample with empty contexts
        and response (these must be filled by running the pipeline or provided separately).
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []

        samples: list[EvaluationSample] = []
        for item in raw:
            try:
                entry = GoldenSetEntry(**item)
            except (TypeError, ValueError):
                logger.warning("Skipping invalid golden set entry: %s", item)
                continue

            samples.append(
                EvaluationSample(
                    query=entry.query,
                    contexts=[],
                    response="",
                    expected_answer=", ".join(entry.expected_answer_keywords),
                )
            )
        return samples
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_input_loader.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/input_loader.py packages/evaluator/tests/test_input_loader.py
git commit -m "feat(evaluator): add InputLoader for JSONL telemetry and golden set files"
```

---

## Task 3: JudgeProvider Protocol + MockJudge

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/judge/base.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/judge/mock_judge.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/judge/__init__.py`
- Create: `packages/evaluator/tests/test_metrics.py`

- [ ] **Step 1: Create the judge directory**

Run: `mkdir -p packages/evaluator/src/rag_forge_evaluator/judge`

- [ ] **Step 2: Write failing tests**

Create `packages/evaluator/tests/test_metrics.py`:

```python
"""Tests for judge providers and evaluation metrics."""

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.mock_judge import MockJudge


class TestMockJudge:
    def test_implements_protocol(self) -> None:
        assert isinstance(MockJudge(), JudgeProvider)

    def test_returns_valid_json(self) -> None:
        judge = MockJudge()
        result = judge.judge("system", "user")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_model_name(self) -> None:
        assert MockJudge().model_name() == "mock-judge"

    def test_custom_response(self) -> None:
        judge = MockJudge(fixed_response='{"score": 0.95}')
        result = judge.judge("system", "user")
        assert '"score": 0.95' in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_metrics.py::TestMockJudge -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement JudgeProvider protocol and MockJudge**

Create `packages/evaluator/src/rag_forge_evaluator/judge/base.py`:

```python
"""Base protocol for LLM judge providers."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class JudgeProvider(Protocol):
    """Protocol for LLM judges that score RAG pipeline outputs."""

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt to the LLM judge and return the response text."""
        ...

    def model_name(self) -> str:
        """Return the name of the judge model."""
        ...
```

Create `packages/evaluator/src/rag_forge_evaluator/judge/mock_judge.py`:

```python
"""Deterministic mock judge for testing. Returns configurable fixed responses."""

import json


_DEFAULT_RESPONSE = json.dumps({
    "claims": [
        {"text": "claim 1", "supported": True},
        {"text": "claim 2", "supported": True},
    ],
    "score": 0.9,
    "ratings": [{"chunk_index": 0, "score": 4, "reason": "relevant"}],
    "mean_score": 0.8,
    "completeness": 4,
    "correctness": 4,
    "coherence": 4,
    "overall_score": 0.8,
    "unsupported_count": 0,
    "total_claims": 2,
    "hallucination_rate": 0.0,
})


class MockJudge:
    """Returns deterministic JSON for all judge calls. Used in all tests."""

    def __init__(self, fixed_response: str | None = None) -> None:
        self._response = fixed_response or _DEFAULT_RESPONSE

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        """Return the fixed response regardless of input."""
        _ = system_prompt, user_prompt
        return self._response

    def model_name(self) -> str:
        return "mock-judge"
```

Create `packages/evaluator/src/rag_forge_evaluator/judge/__init__.py`:

```python
"""LLM judge providers: Claude, OpenAI, and mock for testing."""

from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.mock_judge import MockJudge

__all__ = ["JudgeProvider", "MockJudge"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_metrics.py::TestMockJudge -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/judge/ packages/evaluator/tests/test_metrics.py
git commit -m "feat(evaluator): add JudgeProvider protocol and MockJudge"
```

---

## Task 4: Claude + OpenAI Judge Implementations

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/judge/claude_judge.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/judge/openai_judge.py`

- [ ] **Step 1: Implement ClaudeJudge**

Create `packages/evaluator/src/rag_forge_evaluator/judge/claude_judge.py`:

```python
"""Claude judge provider via Anthropic SDK."""

import os

from anthropic import Anthropic


class ClaudeJudge:
    """Uses Claude to score RAG pipeline outputs.

    Reads ANTHROPIC_API_KEY from environment.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 1024,
    ) -> None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            msg = (
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key to ClaudeJudge."
            )
            raise ValueError(msg)
        self._client = Anthropic(api_key=key)
        self._model = model
        self._max_tokens = max_tokens

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt to Claude and return the response text."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    def model_name(self) -> str:
        return self._model
```

- [ ] **Step 2: Implement OpenAIJudge**

Create `packages/evaluator/src/rag_forge_evaluator/judge/openai_judge.py`:

```python
"""OpenAI judge provider via OpenAI SDK."""

import os

from openai import OpenAI


class OpenAIJudge:
    """Uses GPT-4o to score RAG pipeline outputs.

    Reads OPENAI_API_KEY from environment.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        max_tokens: int = 1024,
    ) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            msg = (
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key to OpenAIJudge."
            )
            raise ValueError(msg)
        self._client = OpenAI(api_key=key)
        self._model = model
        self._max_tokens = max_tokens

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt to GPT-4o and return the response text."""
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def model_name(self) -> str:
        return self._model
```

- [ ] **Step 3: Lint and typecheck**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run ruff check packages/evaluator/src/rag_forge_evaluator/judge/ && uv run mypy packages/evaluator/src/rag_forge_evaluator/judge/`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/judge/claude_judge.py packages/evaluator/src/rag_forge_evaluator/judge/openai_judge.py
git commit -m "feat(evaluator): add Claude and OpenAI judge providers"
```

---

## Task 5: MetricEvaluator Protocol

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/metrics/base.py`

- [ ] **Step 1: Implement the MetricEvaluator protocol**

Create `packages/evaluator/src/rag_forge_evaluator/metrics/base.py`:

```python
"""Base protocol for individual evaluation metrics."""

from typing import Protocol, runtime_checkable

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider


@runtime_checkable
class MetricEvaluator(Protocol):
    """Protocol for individual metric evaluators."""

    def name(self) -> str:
        """Return the metric name (e.g., 'faithfulness')."""
        ...

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        """Evaluate a single sample using the provided judge. Returns a MetricResult."""
        ...

    def default_threshold(self) -> float:
        """Return the default pass/fail threshold for this metric."""
        ...
```

- [ ] **Step 2: Lint and commit**

```bash
uv run ruff check packages/evaluator/src/rag_forge_evaluator/metrics/base.py
git add packages/evaluator/src/rag_forge_evaluator/metrics/base.py
git commit -m "feat(evaluator): add MetricEvaluator protocol"
```

---

## Task 6: Four Evaluation Metrics

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/metrics/faithfulness.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/metrics/context_relevance.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/metrics/answer_relevance.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/metrics/hallucination.py`
- Modify: `packages/evaluator/src/rag_forge_evaluator/metrics/__init__.py`
- Test: `packages/evaluator/tests/test_metrics.py` (append)

- [ ] **Step 1: Write failing tests for all four metrics**

Append to `packages/evaluator/tests/test_metrics.py`:

```python
from rag_forge_evaluator.metrics.faithfulness import FaithfulnessMetric
from rag_forge_evaluator.metrics.context_relevance import ContextRelevanceMetric
from rag_forge_evaluator.metrics.answer_relevance import AnswerRelevanceMetric
from rag_forge_evaluator.metrics.hallucination import HallucinationMetric
from rag_forge_evaluator.engine import MetricResult


def _sample() -> EvaluationSample:
    return EvaluationSample(
        query="What is Python?",
        contexts=["Python is a programming language created by Guido van Rossum."],
        response="Python is a popular programming language.",
    )


class TestFaithfulnessMetric:
    def test_name(self) -> None:
        assert FaithfulnessMetric().name() == "faithfulness"

    def test_default_threshold(self) -> None:
        assert FaithfulnessMetric().default_threshold() == 0.85

    def test_evaluate_sample_returns_metric_result(self) -> None:
        judge = MockJudge()
        result = FaithfulnessMetric().evaluate_sample(_sample(), judge)
        assert isinstance(result, MetricResult)
        assert result.name == "faithfulness"
        assert 0.0 <= result.score <= 1.0

    def test_handles_invalid_json(self) -> None:
        judge = MockJudge(fixed_response="not json")
        result = FaithfulnessMetric().evaluate_sample(_sample(), judge)
        assert result.score == 0.0
        assert not result.passed


class TestContextRelevanceMetric:
    def test_name(self) -> None:
        assert ContextRelevanceMetric().name() == "context_relevance"

    def test_default_threshold(self) -> None:
        assert ContextRelevanceMetric().default_threshold() == 0.80

    def test_evaluate_sample_returns_metric_result(self) -> None:
        judge = MockJudge()
        result = ContextRelevanceMetric().evaluate_sample(_sample(), judge)
        assert isinstance(result, MetricResult)
        assert 0.0 <= result.score <= 1.0


class TestAnswerRelevanceMetric:
    def test_name(self) -> None:
        assert AnswerRelevanceMetric().name() == "answer_relevance"

    def test_default_threshold(self) -> None:
        assert AnswerRelevanceMetric().default_threshold() == 0.80

    def test_evaluate_sample_returns_metric_result(self) -> None:
        judge = MockJudge()
        result = AnswerRelevanceMetric().evaluate_sample(_sample(), judge)
        assert isinstance(result, MetricResult)
        assert 0.0 <= result.score <= 1.0


class TestHallucinationMetric:
    def test_name(self) -> None:
        assert HallucinationMetric().name() == "hallucination"

    def test_default_threshold(self) -> None:
        assert HallucinationMetric().default_threshold() == 0.95

    def test_evaluate_sample_returns_metric_result(self) -> None:
        judge = MockJudge()
        result = HallucinationMetric().evaluate_sample(_sample(), judge)
        assert isinstance(result, MetricResult)
        assert 0.0 <= result.score <= 1.0

    def test_handles_invalid_json(self) -> None:
        judge = MockJudge(fixed_response="garbage")
        result = HallucinationMetric().evaluate_sample(_sample(), judge)
        assert result.score == 0.0
        assert not result.passed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_metrics.py -v -k "Faithfulness or ContextRelevance or AnswerRelevance or Hallucination"`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement FaithfulnessMetric**

Create `packages/evaluator/src/rag_forge_evaluator/metrics/faithfulness.py`:

```python
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
    """Measures whether the response is grounded in the retrieved contexts."""

    def name(self) -> str:
        return "faithfulness"

    def default_threshold(self) -> float:
        return 0.85

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        """Score faithfulness by checking claims against context."""
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
```

- [ ] **Step 4: Implement ContextRelevanceMetric**

Create `packages/evaluator/src/rag_forge_evaluator/metrics/context_relevance.py`:

```python
"""Context relevance metric: are the retrieved chunks relevant to the query?"""

import json
import logging

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert evaluator assessing whether retrieved context chunks are relevant to a query.

Rate each context chunk's relevance to the query on a 1-5 scale:
1 = Completely irrelevant
2 = Slightly relevant
3 = Moderately relevant
4 = Highly relevant
5 = Perfectly relevant

Respond with ONLY valid JSON in this exact format:
{"ratings": [{"chunk_index": 0, "score": 4, "reason": "brief reason"}], "mean_score": 0.8}

The mean_score should be the average rating divided by 5 (normalized to 0.0-1.0)."""


class ContextRelevanceMetric:
    """Measures whether the retrieved chunks are relevant to the query."""

    def name(self) -> str:
        return "context_relevance"

    def default_threshold(self) -> float:
        return 0.80

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        """Score context relevance by rating each chunk."""
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
```

- [ ] **Step 5: Implement AnswerRelevanceMetric**

Create `packages/evaluator/src/rag_forge_evaluator/metrics/answer_relevance.py`:

```python
"""Answer relevance metric: does the response address the question asked?"""

import json
import logging

from rag_forge_evaluator.engine import EvaluationSample, MetricResult
from rag_forge_evaluator.judge.base import JudgeProvider

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
    """Measures whether the response addresses the question asked."""

    def name(self) -> str:
        return "answer_relevance"

    def default_threshold(self) -> float:
        return 0.80

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        """Score answer relevance on completeness, correctness, and coherence."""
        user_prompt = f"Query: {sample.query}\n\nResponse: {sample.response}"

        try:
            raw = judge.judge(_SYSTEM_PROMPT, user_prompt)
            data = json.loads(raw)
            score = float(data.get("overall_score", 0.0))
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Answer relevance eval failed: %s", e)
            return MetricResult(
                name="answer_relevance",
                score=0.0,
                threshold=self.default_threshold(),
                passed=False,
                details=f"Judge returned invalid response: {e}",
            )

        return MetricResult(
            name="answer_relevance",
            score=score,
            threshold=self.default_threshold(),
            passed=score >= self.default_threshold(),
        )
```

- [ ] **Step 6: Implement HallucinationMetric**

Create `packages/evaluator/src/rag_forge_evaluator/metrics/hallucination.py`:

```python
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
    """Measures the percentage of claims without source support."""

    def name(self) -> str:
        return "hallucination"

    def default_threshold(self) -> float:
        return 0.95

    def evaluate_sample(
        self, sample: EvaluationSample, judge: JudgeProvider
    ) -> MetricResult:
        """Score hallucination rate (inverted: higher = better)."""
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
```

- [ ] **Step 7: Update metrics __init__.py**

Replace `packages/evaluator/src/rag_forge_evaluator/metrics/__init__.py`:

```python
"""Evaluation metrics: faithfulness, context relevance, answer relevance, hallucination."""

from rag_forge_evaluator.metrics.base import MetricEvaluator

__all__ = ["MetricEvaluator"]
```

- [ ] **Step 8: Run all metric tests**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_metrics.py -v`
Expected: All 18 tests pass (4 MockJudge + 4 Faithfulness + 3 ContextRelevance + 3 AnswerRelevance + 4 Hallucination)

- [ ] **Step 9: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/metrics/ packages/evaluator/tests/test_metrics.py
git commit -m "feat(evaluator): add four LLM-as-Judge metrics (faithfulness, relevance, hallucination)"
```

---

## Task 7: LLMJudgeEvaluator

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py`
- Test: `packages/evaluator/tests/test_metrics.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `packages/evaluator/tests/test_metrics.py`:

```python
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator
from rag_forge_evaluator.engine import EvaluationResult


class TestLLMJudgeEvaluator:
    def test_evaluate_returns_result(self) -> None:
        judge = MockJudge()
        evaluator = LLMJudgeEvaluator(judge)
        result = evaluator.evaluate([_sample()])
        assert isinstance(result, EvaluationResult)
        assert result.samples_evaluated == 1
        assert len(result.metrics) == 4  # faithfulness, context_relevance, answer_relevance, hallucination

    def test_supported_metrics(self) -> None:
        evaluator = LLMJudgeEvaluator(MockJudge())
        names = evaluator.supported_metrics()
        assert "faithfulness" in names
        assert "context_relevance" in names
        assert "answer_relevance" in names
        assert "hallucination" in names

    def test_overall_score_is_mean(self) -> None:
        evaluator = LLMJudgeEvaluator(MockJudge())
        result = evaluator.evaluate([_sample()])
        scores = [m.score for m in result.metrics]
        expected_mean = sum(scores) / len(scores)
        assert abs(result.overall_score - expected_mean) < 0.01

    def test_custom_thresholds(self) -> None:
        evaluator = LLMJudgeEvaluator(
            MockJudge(),
            thresholds={"faithfulness": 0.99},
        )
        result = evaluator.evaluate([_sample()])
        faith = next(m for m in result.metrics if m.name == "faithfulness")
        assert faith.threshold == 0.99

    def test_empty_samples(self) -> None:
        evaluator = LLMJudgeEvaluator(MockJudge())
        result = evaluator.evaluate([])
        assert result.samples_evaluated == 0
        assert result.overall_score == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_metrics.py::TestLLMJudgeEvaluator -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement LLMJudgeEvaluator**

Create `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py`:

```python
"""LLM-as-Judge evaluator that delegates to individual metric evaluators."""

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
)
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.metrics.answer_relevance import AnswerRelevanceMetric
from rag_forge_evaluator.metrics.base import MetricEvaluator
from rag_forge_evaluator.metrics.context_relevance import ContextRelevanceMetric
from rag_forge_evaluator.metrics.faithfulness import FaithfulnessMetric
from rag_forge_evaluator.metrics.hallucination import HallucinationMetric


def _default_metrics() -> list[MetricEvaluator]:
    return [
        FaithfulnessMetric(),
        ContextRelevanceMetric(),
        AnswerRelevanceMetric(),
        HallucinationMetric(),
    ]


class LLMJudgeEvaluator(EvaluatorInterface):
    """Evaluates RAG samples using LLM-as-Judge across multiple metrics."""

    def __init__(
        self,
        judge: JudgeProvider,
        metrics: list[MetricEvaluator] | None = None,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        self._judge = judge
        self._metrics = metrics or _default_metrics()
        self._thresholds = thresholds or {}

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        """Evaluate all samples across all metrics."""
        if not samples:
            return EvaluationResult(
                metrics=[], overall_score=0.0, samples_evaluated=0, passed=False
            )

        # Collect per-metric scores across all samples
        metric_scores: dict[str, list[float]] = {m.name(): [] for m in self._metrics}

        for sample in samples:
            for metric in self._metrics:
                result = metric.evaluate_sample(sample, self._judge)
                metric_scores[metric.name()].append(result.score)

        # Aggregate: mean score per metric
        aggregated: list[MetricResult] = []
        for metric in self._metrics:
            scores = metric_scores[metric.name()]
            mean_score = sum(scores) / len(scores) if scores else 0.0
            threshold = self._thresholds.get(metric.name(), metric.default_threshold())
            aggregated.append(
                MetricResult(
                    name=metric.name(),
                    score=round(mean_score, 4),
                    threshold=threshold,
                    passed=mean_score >= threshold,
                )
            )

        overall = sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        all_passed = all(m.passed for m in aggregated)

        return EvaluationResult(
            metrics=aggregated,
            overall_score=round(overall, 4),
            samples_evaluated=len(samples),
            passed=all_passed,
        )

    def supported_metrics(self) -> list[str]:
        return [m.name() for m in self._metrics]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_metrics.py -v`
Expected: All tests pass (MockJudge + 4 metrics + LLMJudgeEvaluator = ~23 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py packages/evaluator/tests/test_metrics.py
git commit -m "feat(evaluator): add LLMJudgeEvaluator orchestrating four metrics"
```

---

## Task 8: RMM Scorer Enhancement

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/maturity.py`
- Modify: `packages/evaluator/tests/test_maturity.py`

- [ ] **Step 1: Write failing tests for real scoring logic**

Append to `packages/evaluator/tests/test_maturity.py`:

```python
class TestRMMScorerLogic:
    def test_empty_metrics_returns_naive(self) -> None:
        assert RMMScorer().assess({}) == RMMLevel.NAIVE

    def test_trust_level_with_good_scores(self) -> None:
        metrics = {"faithfulness": 0.90, "context_relevance": 0.85}
        assert RMMScorer().assess(metrics) == RMMLevel.TRUST

    def test_trust_level_fails_with_low_faithfulness(self) -> None:
        metrics = {"faithfulness": 0.70, "context_relevance": 0.85}
        result = RMMScorer().assess(metrics)
        assert result < RMMLevel.TRUST

    def test_trust_level_fails_with_low_relevance(self) -> None:
        metrics = {"faithfulness": 0.90, "context_relevance": 0.50}
        result = RMMScorer().assess(metrics)
        assert result < RMMLevel.TRUST

    def test_caps_at_trust_for_phase1(self) -> None:
        metrics = {
            "faithfulness": 0.95,
            "context_relevance": 0.90,
            "answer_relevance": 0.90,
            "hallucination": 0.98,
        }
        result = RMMScorer().assess(metrics)
        assert result <= RMMLevel.TRUST
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_maturity.py::TestRMMScorerLogic -v`
Expected: Some fail (scorer always returns NAIVE)

- [ ] **Step 3: Implement real scoring logic**

Replace `RMMScorer` class in `packages/evaluator/src/rag_forge_evaluator/maturity.py` (keep everything else unchanged):

```python
class RMMScorer:
    """Scores a RAG pipeline against the RAG Maturity Model.

    For Phase 1, only RMM-0 through RMM-3 are checkable. Higher levels
    require infrastructure features (caching, RBAC) not yet available.
    """

    def assess(self, metrics: dict[str, float]) -> RMMLevel:
        """Determine the RMM level based on pipeline metrics.

        Walks from RMM-0 upward. Returns the highest level where all
        checkable requirements are met.
        """
        level = RMMLevel.NAIVE

        # RMM-1 (Recall): requires recall_at_k >= 0.70
        if metrics.get("recall_at_k", 0.0) >= 0.70:
            level = RMMLevel.RECALL

            # RMM-2 (Precision): requires reranker improvement
            if metrics.get("ndcg_improvement", 0.0) >= 0.10:
                level = RMMLevel.PRECISION

        # RMM-3 (Trust): requires faithfulness >= 0.85 AND context_relevance >= 0.80
        # Trust can be reached directly if faith + relevance are good,
        # even without explicit recall/precision metrics
        faithfulness = metrics.get("faithfulness", 0.0)
        context_relevance = metrics.get("context_relevance", 0.0)

        if faithfulness >= 0.85 and context_relevance >= 0.80:
            level = max(level, RMMLevel.TRUST)

        # RMM-4 and RMM-5 require infrastructure not available in Phase 1
        # (caching, latency tracking, RBAC, drift detection)

        return level
```

- [ ] **Step 4: Run all maturity tests**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_maturity.py -v`
Expected: All tests pass (original + new)

- [ ] **Step 5: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/maturity.py packages/evaluator/tests/test_maturity.py
git commit -m "feat(evaluator): implement RMM scoring logic (levels 0-3)"
```

---

## Task 9: HTML Report Generator

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/report/generator.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2`
- Create: `packages/evaluator/tests/test_report.py`

- [ ] **Step 1: Write failing tests**

Create `packages/evaluator/tests/test_report.py`:

```python
"""Tests for the HTML report generator."""

from pathlib import Path

from rag_forge_evaluator.engine import EvaluationResult, MetricResult
from rag_forge_evaluator.maturity import RMMLevel
from rag_forge_evaluator.report.generator import ReportGenerator


def _mock_result() -> EvaluationResult:
    return EvaluationResult(
        metrics=[
            MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
            MetricResult(name="context_relevance", score=0.75, threshold=0.80, passed=False),
            MetricResult(name="answer_relevance", score=0.88, threshold=0.80, passed=True),
            MetricResult(name="hallucination", score=0.96, threshold=0.95, passed=True),
        ],
        overall_score=0.87,
        samples_evaluated=10,
        passed=False,
    )


class TestReportGenerator:
    def test_generates_html_file(self, tmp_path: Path) -> None:
        gen = ReportGenerator(output_dir=tmp_path)
        path = gen.generate_html(_mock_result(), RMMLevel.NAIVE)
        assert path.exists()
        assert path.suffix == ".html"

    def test_html_contains_rmm_badge(self, tmp_path: Path) -> None:
        gen = ReportGenerator(output_dir=tmp_path)
        path = gen.generate_html(_mock_result(), RMMLevel.TRUST)
        html = path.read_text(encoding="utf-8")
        assert "RMM-3" in html
        assert "Better Trust" in html

    def test_html_contains_metric_scores(self, tmp_path: Path) -> None:
        gen = ReportGenerator(output_dir=tmp_path)
        path = gen.generate_html(_mock_result(), RMMLevel.NAIVE)
        html = path.read_text(encoding="utf-8")
        assert "faithfulness" in html
        assert "0.90" in html or "0.9" in html
        assert "PASS" in html
        assert "FAIL" in html

    def test_html_contains_overall_score(self, tmp_path: Path) -> None:
        gen = ReportGenerator(output_dir=tmp_path)
        path = gen.generate_html(_mock_result(), RMMLevel.NAIVE)
        html = path.read_text(encoding="utf-8")
        assert "0.87" in html

    def test_html_is_standalone(self, tmp_path: Path) -> None:
        gen = ReportGenerator(output_dir=tmp_path)
        path = gen.generate_html(_mock_result(), RMMLevel.NAIVE)
        html = path.read_text(encoding="utf-8")
        assert "<html" in html
        assert "<style" in html
        assert "RAG-Forge" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_report.py -v`
Expected: FAIL — generate_html signature doesn't match

- [ ] **Step 3: Create Jinja2 HTML template**

Run: `mkdir -p packages/evaluator/src/rag_forge_evaluator/report/templates`

Create `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG-Forge Audit Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 2rem; }
        .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 2rem; }
        h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
        .timestamp { color: #666; font-size: 0.9rem; margin-bottom: 2rem; }
        .badge { display: inline-block; padding: 0.5rem 1rem; border-radius: 4px; font-weight: bold; font-size: 1.1rem; margin-bottom: 1.5rem; }
        .badge-green { background: #d4edda; color: #155724; }
        .badge-yellow { background: #fff3cd; color: #856404; }
        .badge-red { background: #f8d7da; color: #721c24; }
        .summary { display: flex; gap: 2rem; margin-bottom: 2rem; }
        .summary-card { flex: 1; padding: 1rem; border: 1px solid #ddd; border-radius: 4px; text-align: center; }
        .summary-card .value { font-size: 2rem; font-weight: bold; }
        .summary-card .label { color: #666; font-size: 0.85rem; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        .pass { color: #155724; font-weight: bold; }
        .fail { color: #721c24; font-weight: bold; }
        .recommendations { background: #f8f9fa; padding: 1.5rem; border-radius: 4px; margin-bottom: 2rem; }
        .recommendations h2 { font-size: 1.2rem; margin-bottom: 1rem; }
        .recommendations li { margin-bottom: 0.5rem; padding-left: 0.5rem; }
        .footer { text-align: center; color: #999; font-size: 0.8rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <h1>RAG-Forge Audit Report</h1>
        <p class="timestamp">Generated: {{ timestamp }}</p>

        {% if rmm_level <= 1 %}
        <div class="badge badge-red">RMM-{{ rmm_level }}: {{ rmm_name }}</div>
        {% elif rmm_level <= 3 %}
        <div class="badge badge-yellow">RMM-{{ rmm_level }}: {{ rmm_name }}</div>
        {% else %}
        <div class="badge badge-green">RMM-{{ rmm_level }}: {{ rmm_name }}</div>
        {% endif %}

        <div class="summary">
            <div class="summary-card">
                <div class="value">{{ "%.2f"|format(overall_score) }}</div>
                <div class="label">Overall Score</div>
            </div>
            <div class="summary-card">
                <div class="value {% if passed %}pass{% else %}fail{% endif %}">{{ "PASS" if passed else "FAIL" }}</div>
                <div class="label">Status</div>
            </div>
            <div class="summary-card">
                <div class="value">{{ samples_evaluated }}</div>
                <div class="label">Samples Evaluated</div>
            </div>
        </div>

        <h2>Metrics</h2>
        <table>
            <thead>
                <tr><th>Metric</th><th>Score</th><th>Threshold</th><th>Status</th></tr>
            </thead>
            <tbody>
                {% for m in metrics %}
                <tr>
                    <td>{{ m.name }}</td>
                    <td>{{ "%.2f"|format(m.score) }}</td>
                    <td>{{ "%.2f"|format(m.threshold) }}</td>
                    <td class="{% if m.passed %}pass{% else %}fail{% endif %}">{{ "PASS" if m.passed else "FAIL" }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        {% if recommendations %}
        <div class="recommendations">
            <h2>Recommendations</h2>
            <ul>
                {% for rec in recommendations %}
                <li>{{ rec }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        <div class="footer">Generated by RAG-Forge v0.1.0</div>
    </div>
</body>
</html>
```

- [ ] **Step 4: Rewrite ReportGenerator**

Replace `packages/evaluator/src/rag_forge_evaluator/report/generator.py`:

```python
"""HTML audit report generator using Jinja2 templates."""

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rag_forge_evaluator.engine import EvaluationResult
from rag_forge_evaluator.maturity import RMM_CRITERIA, RMMLevel

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _generate_recommendations(result: EvaluationResult) -> list[str]:
    """Generate actionable recommendations based on metric results."""
    recs: list[str] = []
    for m in result.metrics:
        if not m.passed:
            gap = m.threshold - m.score
            recs.append(
                f"Improve {m.name}: current score {m.score:.2f} is {gap:.2f} below "
                f"threshold {m.threshold:.2f}."
            )
    if not result.metrics:
        recs.append("No metrics were evaluated. Run with --input or --golden-set.")
    return recs


class ReportGenerator:
    """Generates standalone HTML audit reports from evaluation results."""

    def __init__(self, output_dir: str | Path = "./reports") -> None:
        self.output_dir = Path(output_dir)

    def generate_html(
        self, result: EvaluationResult, rmm_level: RMMLevel
    ) -> Path:
        """Generate a standalone HTML report."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=True,
        )
        template = env.get_template("audit_report.html.j2")

        rmm_name = next(
            (c.name for c in RMM_CRITERIA if c.level == rmm_level),
            "Unknown",
        )

        html = template.render(
            timestamp=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            rmm_level=int(rmm_level),
            rmm_name=rmm_name,
            overall_score=result.overall_score,
            passed=result.passed,
            samples_evaluated=result.samples_evaluated,
            metrics=result.metrics,
            recommendations=_generate_recommendations(result),
        )

        output_path = self.output_dir / "audit-report.html"
        output_path.write_text(html, encoding="utf-8")
        return output_path
```

- [ ] **Step 5: Run tests**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_report.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/report/ packages/evaluator/tests/test_report.py
git commit -m "feat(evaluator): add Jinja2 HTML audit report generator"
```

---

## Task 10: Audit Orchestrator

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/audit.py`
- Create: `packages/evaluator/tests/test_audit.py`

- [ ] **Step 1: Write failing integration test**

Create `packages/evaluator/tests/test_audit.py`:

```python
"""Integration tests for the audit orchestrator."""

import json
from pathlib import Path

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator, AuditReport
from rag_forge_evaluator.maturity import RMMLevel


class TestAuditOrchestrator:
    def _make_jsonl(self, tmp_path: Path) -> Path:
        jsonl = tmp_path / "telemetry.jsonl"
        lines = [
            {"query": "What is Python?", "contexts": ["Python is a language."], "response": "Python is a programming language."},
            {"query": "What is Rust?", "contexts": ["Rust is fast."], "response": "Rust is a systems programming language."},
            {"query": "What is Go?", "contexts": ["Go is concurrent."], "response": "Go is a language by Google."},
        ]
        jsonl.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
        return jsonl

    def test_full_audit_from_jsonl(self, tmp_path: Path) -> None:
        jsonl = self._make_jsonl(tmp_path)
        config = AuditConfig(
            input_path=jsonl,
            judge_model="mock",
            output_dir=tmp_path / "reports",
        )
        report = AuditOrchestrator(config).run()
        assert isinstance(report, AuditReport)
        assert report.samples_evaluated == 3
        assert report.evaluation.samples_evaluated == 3
        assert len(report.evaluation.metrics) == 4
        assert report.report_path.exists()

    def test_audit_generates_html(self, tmp_path: Path) -> None:
        jsonl = self._make_jsonl(tmp_path)
        config = AuditConfig(
            input_path=jsonl,
            judge_model="mock",
            output_dir=tmp_path / "reports",
        )
        report = AuditOrchestrator(config).run()
        html = report.report_path.read_text(encoding="utf-8")
        assert "RAG-Forge Audit Report" in html
        assert "faithfulness" in html

    def test_audit_with_golden_set(self, tmp_path: Path) -> None:
        gs = tmp_path / "golden.json"
        gs.write_text(
            json.dumps([
                {"query": "What is RAG?", "expected_answer_keywords": ["retrieval", "augmented"]},
            ]),
            encoding="utf-8",
        )
        config = AuditConfig(
            golden_set_path=gs,
            judge_model="mock",
            output_dir=tmp_path / "reports",
        )
        report = AuditOrchestrator(config).run()
        assert report.samples_evaluated == 1

    def test_audit_rmm_level(self, tmp_path: Path) -> None:
        jsonl = self._make_jsonl(tmp_path)
        config = AuditConfig(
            input_path=jsonl,
            judge_model="mock",
            output_dir=tmp_path / "reports",
        )
        report = AuditOrchestrator(config).run()
        assert isinstance(report.rmm_level, RMMLevel)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_audit.py -v`
Expected: FAIL — AuditOrchestrator.run() returns wrong type

- [ ] **Step 3: Rewrite audit.py**

Replace `packages/evaluator/src/rag_forge_evaluator/audit.py`:

```python
"""Audit orchestrator: coordinates evaluation and report generation."""

from dataclasses import dataclass
from pathlib import Path

from rag_forge_evaluator.engine import EvaluationResult
from rag_forge_evaluator.input_loader import InputLoader
from rag_forge_evaluator.judge.mock_judge import MockJudge
from rag_forge_evaluator.maturity import RMMLevel, RMMScorer
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator
from rag_forge_evaluator.report.generator import ReportGenerator


@dataclass
class AuditConfig:
    """Configuration for an audit run."""

    input_path: Path | None = None
    golden_set_path: Path | None = None
    judge_model: str | None = None
    output_dir: Path = Path("./reports")
    generate_pdf: bool = False
    thresholds: dict[str, float] | None = None


@dataclass
class AuditReport:
    """Complete audit report with evaluation results and RMM scoring."""

    evaluation: EvaluationResult
    rmm_level: RMMLevel
    report_path: Path
    samples_evaluated: int


def _create_judge(model: str | None):  # noqa: ANN201
    """Create a judge provider based on model name."""
    if model == "mock" or model is None:
        return MockJudge()
    if model in ("claude", "claude-sonnet"):
        from rag_forge_evaluator.judge.claude_judge import ClaudeJudge
        return ClaudeJudge()
    if model in ("openai", "gpt-4o"):
        from rag_forge_evaluator.judge.openai_judge import OpenAIJudge
        return OpenAIJudge()
    return MockJudge()


class AuditOrchestrator:
    """Orchestrates the full audit pipeline.

    1. Load telemetry data (JSONL) or golden set
    2. Run evaluation metrics via LLM-as-Judge
    3. Score against RAG Maturity Model
    4. Generate HTML report
    """

    def __init__(self, config: AuditConfig) -> None:
        self.config = config

    def run(self) -> AuditReport:
        """Execute the full audit pipeline."""
        # 1. Load input
        if self.config.input_path:
            samples = InputLoader.load_jsonl(self.config.input_path)
        elif self.config.golden_set_path:
            samples = InputLoader.load_golden_set(self.config.golden_set_path)
        else:
            msg = "Either input_path or golden_set_path must be provided"
            raise ValueError(msg)

        # 2. Create judge and evaluator
        judge = _create_judge(self.config.judge_model)
        evaluator = LLMJudgeEvaluator(
            judge=judge,
            thresholds=self.config.thresholds,
        )

        # 3. Run evaluation
        evaluation = evaluator.evaluate(samples)

        # 4. Score against RMM
        metric_map = {m.name: m.score for m in evaluation.metrics}
        rmm_level = RMMScorer().assess(metric_map)

        # 5. Generate report
        generator = ReportGenerator(output_dir=self.config.output_dir)
        report_path = generator.generate_html(evaluation, rmm_level)

        return AuditReport(
            evaluation=evaluation,
            rmm_level=rmm_level,
            report_path=report_path,
            samples_evaluated=evaluation.samples_evaluated,
        )
```

- [ ] **Step 4: Run integration tests**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/test_audit.py -v`
Expected: 4 passed

- [ ] **Step 5: Run full evaluator test suite**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/ -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/audit.py packages/evaluator/tests/test_audit.py
git commit -m "feat(evaluator): implement AuditOrchestrator with full evaluation pipeline"
```

---

## Task 11: Evaluator Python CLI

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/cli.py`

- [ ] **Step 1: Implement the evaluator Python CLI**

Create `packages/evaluator/src/rag_forge_evaluator/cli.py`:

```python
"""Python CLI entry point for the rag-forge audit command.

Called via: uv run python -m rag_forge_evaluator.cli audit --input telemetry.jsonl
Outputs JSON to stdout for the TypeScript CLI to parse.
"""

import argparse
import json
import sys
from pathlib import Path

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator


def cmd_audit(args: argparse.Namespace) -> None:
    """Run the audit command."""
    config_data = json.loads(args.config_json) if args.config_json else {}

    config = AuditConfig(
        input_path=Path(args.input) if args.input else None,
        golden_set_path=Path(args.golden_set) if args.golden_set else None,
        judge_model=args.judge or config_data.get("judge_model", "mock"),
        output_dir=Path(args.output),
        thresholds=config_data.get("thresholds"),
    )

    report = AuditOrchestrator(config).run()

    output = {
        "success": True,
        "overall_score": report.evaluation.overall_score,
        "passed": report.evaluation.passed,
        "rmm_level": int(report.rmm_level),
        "rmm_name": report.rmm_level.name,
        "samples_evaluated": report.samples_evaluated,
        "metrics": [
            {"name": m.name, "score": m.score, "threshold": m.threshold, "passed": m.passed}
            for m in report.evaluation.metrics
        ],
        "report_path": str(report.report_path),
    }
    json.dump(output, sys.stdout)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="rag-forge-evaluator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Run evaluation audit")
    audit_parser.add_argument("--input", help="Path to telemetry JSONL file")
    audit_parser.add_argument("--golden-set", help="Path to golden set JSON file")
    audit_parser.add_argument("--judge", help="Judge model: mock | claude | openai")
    audit_parser.add_argument("--output", default="./reports", help="Output directory")
    audit_parser.add_argument("--config-json", help="JSON config from TS CLI")

    args = parser.parse_args()
    if args.command == "audit":
        cmd_audit(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test manually**

Run: `export PATH="$HOME/.local/bin:$PATH" && echo '{"query":"test","contexts":["ctx"],"response":"resp"}' > /tmp/test.jsonl && uv run python -m rag_forge_evaluator.cli audit --input /tmp/test.jsonl --judge mock --output /tmp/reports`
Expected: JSON output with success, metrics, rmm_level

- [ ] **Step 3: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/cli.py
git commit -m "feat(evaluator): add Python CLI entry point for audit command"
```

---

## Task 12: TypeScript CLI Audit Wiring

**Files:**
- Modify: `packages/cli/src/commands/audit.ts`

- [ ] **Step 1: Rewrite audit.ts with Python bridge**

Replace `packages/cli/src/commands/audit.ts`:

```typescript
import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface AuditMetric {
  name: string;
  score: number;
  threshold: number;
  passed: boolean;
}

interface AuditResult {
  success: boolean;
  overall_score: number;
  passed: boolean;
  rmm_level: number;
  rmm_name: string;
  samples_evaluated: number;
  metrics: AuditMetric[];
  report_path: string;
}

export function registerAuditCommand(program: Command): void {
  program
    .command("audit")
    .option("-i, --input <file>", "Path to telemetry JSONL file")
    .option("-g, --golden-set <file>", "Path to golden set JSON file")
    .option("-j, --judge <model>", "Judge model: mock | claude | openai", "mock")
    .option("-o, --output <dir>", "Output directory for reports", "./reports")
    .description("Run evaluation on pipeline telemetry and generate audit report")
    .action(
      async (options: {
        input?: string;
        goldenSet?: string;
        judge: string;
        output: string;
      }) => {
        if (!options.input && !options.goldenSet) {
          logger.error("Either --input or --golden-set is required");
          process.exit(1);
        }

        const spinner = ora("Running RAG pipeline audit...").start();

        try {
          const args = ["audit", "--judge", options.judge, "--output", options.output];

          if (options.input) {
            args.push("--input", options.input);
          }
          if (options.goldenSet) {
            args.push("--golden-set", options.goldenSet);
          }

          const result = await runPythonModule({
            module: "rag_forge_evaluator.cli",
            args,
          });

          if (result.exitCode !== 0) {
            spinner.fail("Audit failed");
            logger.error(result.stderr || "Unknown error during audit");
            process.exit(1);
          }

          const output: AuditResult = JSON.parse(result.stdout);

          if (output.passed) {
            spinner.succeed(`Audit passed — RMM-${String(output.rmm_level)}: ${output.rmm_name}`);
          } else {
            spinner.warn(`Audit completed — RMM-${String(output.rmm_level)}: ${output.rmm_name}`);
          }

          logger.info(`Overall score: ${output.overall_score.toFixed(2)}`);
          logger.info(`Samples evaluated: ${String(output.samples_evaluated)}`);

          for (const metric of output.metrics) {
            const status = metric.passed ? "PASS" : "FAIL";
            logger.info(`  ${metric.name}: ${metric.score.toFixed(2)} (threshold: ${metric.threshold.toFixed(2)}) [${status}]`);
          }

          logger.success(`Report saved to: ${output.report_path}`);
        } catch (error) {
          spinner.fail("Audit failed");
          const message = error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
```

- [ ] **Step 2: Build and verify**

Run: `pnpm run build`
Expected: Both packages build successfully

- [ ] **Step 3: Run TS tests**

Run: `pnpm run test:ts`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add packages/cli/src/commands/audit.ts
git commit -m "feat(cli): wire rag-forge audit command to Python evaluator bridge"
```

---

## Task 13: Full Verification

- [ ] **Step 1: Run all Python tests**

Run: `export PATH="$HOME/.local/bin:$PATH" && uv run pytest packages/evaluator/tests/ packages/core/tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run all TypeScript tests**

Run: `pnpm run test:ts`
Expected: All tests pass

- [ ] **Step 3: Lint everything**

Run: `export PATH="$HOME/.local/bin:$PATH" && pnpm run lint`
Expected: Zero errors

- [ ] **Step 4: Typecheck everything**

Run: `export PATH="$HOME/.local/bin:$PATH" && pnpm run typecheck`
Expected: Zero errors

- [ ] **Step 5: Build everything**

Run: `pnpm run build`
Expected: Zero errors

- [ ] **Step 6: Manual end-to-end test**

```bash
mkdir -p test-audit
echo '{"query":"What is Python?","contexts":["Python is a programming language."],"response":"Python is a popular language for data science."}' > test-audit/telemetry.jsonl
echo '{"query":"What is Rust?","contexts":["Rust is fast and memory safe."],"response":"Rust is a systems programming language."}' >> test-audit/telemetry.jsonl
echo '{"query":"What is Go?","contexts":["Go was created at Google."],"response":"Go is a concurrent programming language by Google."}' >> test-audit/telemetry.jsonl
export PATH="$HOME/.local/bin:$PATH" && uv run python -m rag_forge_evaluator.cli audit --input test-audit/telemetry.jsonl --judge mock --output test-audit/reports
```

Expected: JSON output with `success: true`, 4 metrics, `rmm_level`, `report_path`. Verify the HTML report exists and opens in a browser.

- [ ] **Step 7: Clean up and commit**

```bash
rm -rf test-audit
git add -A
git commit -m "feat(evaluator): complete Phase 1B evaluation pipeline

Implements the full evaluation pipeline:
- Input loading (JSONL telemetry + golden set JSON)
- JudgeProvider abstraction (Claude, GPT-4o, mock)
- Four LLM-as-Judge metrics (faithfulness, context relevance, answer relevance, hallucination)
- LLMJudgeEvaluator orchestrator
- RMM scoring logic (levels 0-3)
- Jinja2 HTML audit report generator
- AuditOrchestrator pipeline
- Python CLI entry point for TypeScript bridge
- TypeScript audit command with Python bridge integration

All tests pass. All lint/typecheck clean."
```

- [ ] **Step 8: Push and create PR**

```bash
git push origin feat/phase1a-data-pipeline
```

Then create a new PR or add to the existing one if it hasn't been merged yet.
