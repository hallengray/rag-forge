# Phase 2C: Evaluation Enhancements + CI/CD Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the evaluation engine with optional RAGAS/DeepEval evaluator engines, an enhanced Lighthouse-quality HTML report (radar chart, per-sample breakdown, trend arrows, root cause analysis), audit history tracking, machine-readable JSON output, and an active CI/CD gate workflow.

**Architecture:** The existing `EvaluatorInterface` ABC is the extension point. New evaluator engines (`RagasEvaluator`, `DeepEvalEvaluator`) implement it as optional alternatives to `LLMJudgeEvaluator`. The `AuditOrchestrator` selects the engine via config. The report generator is enhanced with new template sections and a JSON output method. History is a simple JSON sidecar file.

**Tech Stack:** Python 3.11+ (jinja2, ragas optional, deepeval optional), GitHub Actions YAML.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/evaluator/src/rag_forge_evaluator/engines/__init__.py` | Evaluator factory: `create_evaluator()` |
| `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py` | RAGAS framework wrapper |
| `packages/evaluator/src/rag_forge_evaluator/engines/deepeval_evaluator.py` | DeepEval framework wrapper |
| `packages/evaluator/src/rag_forge_evaluator/history.py` | Audit history load/append/trend |
| `packages/evaluator/src/rag_forge_evaluator/report/radar.py` | Inline SVG radar chart generator |
| `packages/evaluator/tests/test_evaluator_factory.py` | Factory + engine tests |
| `packages/evaluator/tests/test_history.py` | History load/append/trend tests |
| `packages/evaluator/tests/test_radar_chart.py` | Radar SVG generation tests |
| `packages/evaluator/tests/test_json_report.py` | JSON report output tests |
| `packages/evaluator/tests/test_enhanced_report.py` | Enhanced HTML report tests |
| `packages/evaluator/tests/test_audit_enhanced_integration.py` | Full audit with history integration test |

### Modified Files

| File | Change |
|------|--------|
| `packages/evaluator/pyproject.toml` | Add ragas/deepeval optional deps |
| `packages/evaluator/src/rag_forge_evaluator/engine.py` | Add `SampleResult` dataclass, `sample_results` field to `EvaluationResult` |
| `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py` | Collect per-sample results |
| `packages/evaluator/src/rag_forge_evaluator/audit.py` | Use engine factory, integrate history + JSON output |
| `packages/evaluator/src/rag_forge_evaluator/report/generator.py` | Add `generate_json()`, enhanced `generate_html()` |
| `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2` | Radar chart, trends, per-sample, visual polish |
| `packages/evaluator/src/rag_forge_evaluator/cli.py` | Add `--evaluator` arg |
| `packages/cli/src/commands/audit.ts` | Add `--evaluator` flag |
| `.github/workflows/rag-audit.yml` | Activate CI gate |

---

## Task 1: Add Optional Dependencies

**Files:**
- Modify: `packages/evaluator/pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

Add optional dependency groups for ragas and deepeval:

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

[project.optional-dependencies]
ragas = ["ragas>=0.2"]
deepeval = ["deepeval>=1.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/rag_forge_evaluator"]
```

- [ ] **Step 2: Commit**

```bash
git add packages/evaluator/pyproject.toml
git commit -m "chore(evaluator): add ragas and deepeval optional dependencies"
```

---

## Task 2: SampleResult Dataclass and EvaluationResult Enhancement

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/engine.py`

- [ ] **Step 1: Add SampleResult and update EvaluationResult**

Add after the `MetricResult` dataclass and update `EvaluationResult`:

```python
"""Abstract base for evaluation engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EvaluationSample:
    """A single sample to evaluate."""

    query: str
    contexts: list[str]
    response: str
    expected_answer: str | None = None
    chunk_ids: list[str] | None = None


@dataclass
class MetricResult:
    """Result of a single metric evaluation."""

    name: str
    score: float
    threshold: float
    passed: bool
    details: str | None = None


@dataclass
class SampleResult:
    """Evaluation results for a single sample."""

    query: str
    response: str
    metrics: dict[str, float]
    worst_metric: str
    root_cause: str


@dataclass
class EvaluationResult:
    """Complete evaluation result across all metrics."""

    metrics: list[MetricResult]
    overall_score: float
    samples_evaluated: int
    passed: bool
    sample_results: list[SampleResult] = field(default_factory=list)


class EvaluatorInterface(ABC):
    """Abstract interface that all evaluation engines must implement."""

    @abstractmethod
    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        """Evaluate a list of samples and return aggregated results."""

    @abstractmethod
    def supported_metrics(self) -> list[str]:
        """Return the list of metric names this evaluator supports."""
```

The `root_cause` field is determined by:
- `"retrieval"` if context_relevance is the worst metric (retrieved chunks weren't relevant)
- `"generation"` if faithfulness is the worst metric (LLM hallucinated)
- `"both"` if both are below threshold
- `"none"` if all metrics pass

- [ ] **Step 2: Run existing tests to verify backward compatibility**

Run: `cd packages/evaluator && uv run pytest -v`
Expected: All existing tests PASS (new field has default value).

- [ ] **Step 3: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/engine.py
git commit -m "feat(evaluator): add SampleResult dataclass and per-sample tracking"
```

---

## Task 3: Update LLMJudgeEvaluator to Collect Per-Sample Results

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py`

- [ ] **Step 1: Update LLMJudgeEvaluator.evaluate()**

Replace the full contents of `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py`:

```python
"""LLM-as-Judge evaluator that delegates to individual metric evaluators."""

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
    SampleResult,
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


def _determine_root_cause(
    sample_metrics: dict[str, float], thresholds: dict[str, float]
) -> str:
    """Determine whether a poor result is due to retrieval, generation, or both."""
    retrieval_fail = sample_metrics.get("context_relevance", 1.0) < thresholds.get(
        "context_relevance", 0.80
    )
    generation_fail = sample_metrics.get("faithfulness", 1.0) < thresholds.get(
        "faithfulness", 0.85
    )
    if retrieval_fail and generation_fail:
        return "both"
    if retrieval_fail:
        return "retrieval"
    if generation_fail:
        return "generation"
    return "none"


class LLMJudgeEvaluator(EvaluatorInterface):
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
        if not samples:
            return EvaluationResult(
                metrics=[],
                overall_score=0.0,
                samples_evaluated=0,
                passed=False,
            )

        metric_scores: dict[str, list[float]] = {m.name(): [] for m in self._metrics}
        sample_results: list[SampleResult] = []

        for sample in samples:
            sample_metric_scores: dict[str, float] = {}
            for metric in self._metrics:
                result = metric.evaluate_sample(sample, self._judge)
                metric_scores[metric.name()].append(result.score)
                sample_metric_scores[metric.name()] = result.score

            worst_metric = min(sample_metric_scores, key=sample_metric_scores.get)  # type: ignore[arg-type]
            thresholds_map = {
                m.name(): self._thresholds.get(m.name(), m.default_threshold())
                for m in self._metrics
            }
            root_cause = _determine_root_cause(sample_metric_scores, thresholds_map)

            sample_results.append(
                SampleResult(
                    query=sample.query,
                    response=sample.response,
                    metrics=sample_metric_scores,
                    worst_metric=worst_metric,
                    root_cause=root_cause,
                )
            )

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

        overall = (
            sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        )
        return EvaluationResult(
            metrics=aggregated,
            overall_score=round(overall, 4),
            samples_evaluated=len(samples),
            passed=all(m.passed for m in aggregated),
            sample_results=sample_results,
        )

    def supported_metrics(self) -> list[str]:
        return [m.name() for m in self._metrics]
```

- [ ] **Step 2: Run existing tests**

Run: `cd packages/evaluator && uv run pytest tests/test_metrics.py -v`
Expected: All existing tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py
git commit -m "feat(evaluator): collect per-sample results with root cause analysis"
```

---

## Task 4: Evaluator Engine Factory

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/engines/__init__.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py`
- Create: `packages/evaluator/src/rag_forge_evaluator/engines/deepeval_evaluator.py`
- Test: `packages/evaluator/tests/test_evaluator_factory.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/evaluator/tests/test_evaluator_factory.py`:

```python
"""Tests for evaluator engine factory."""

import pytest

from rag_forge_evaluator.engine import EvaluatorInterface
from rag_forge_evaluator.engines import create_evaluator
from rag_forge_evaluator.judge.mock_judge import MockJudge
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator


class TestCreateEvaluator:
    def test_llm_judge_returns_correct_type(self) -> None:
        evaluator = create_evaluator("llm-judge", judge=MockJudge())
        assert isinstance(evaluator, LLMJudgeEvaluator)
        assert isinstance(evaluator, EvaluatorInterface)

    def test_unknown_engine_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown evaluator engine"):
            create_evaluator("invalid")

    def test_ragas_not_installed_raises(self) -> None:
        """RAGAS is not installed in test env — should raise ImportError."""
        with pytest.raises(ImportError):
            create_evaluator("ragas")

    def test_deepeval_not_installed_raises(self) -> None:
        """DeepEval is not installed in test env — should raise ImportError."""
        with pytest.raises(ImportError):
            create_evaluator("deepeval")

    def test_llm_judge_with_thresholds(self) -> None:
        evaluator = create_evaluator(
            "llm-judge",
            judge=MockJudge(),
            thresholds={"faithfulness": 0.90},
        )
        assert isinstance(evaluator, LLMJudgeEvaluator)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/evaluator && uv run pytest tests/test_evaluator_factory.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementations**

Create `packages/evaluator/src/rag_forge_evaluator/engines/__init__.py`:

```python
"""Evaluator engine factory."""

from rag_forge_evaluator.engine import EvaluatorInterface
from rag_forge_evaluator.judge.base import JudgeProvider


def create_evaluator(
    engine: str,
    judge: JudgeProvider | None = None,
    thresholds: dict[str, float] | None = None,
) -> EvaluatorInterface:
    """Create an evaluator engine by name.

    Supported engines: llm-judge (default), ragas, deepeval.
    RAGAS and DeepEval require their respective optional dependencies.
    """
    if engine == "llm-judge":
        from rag_forge_evaluator.judge.mock_judge import MockJudge
        from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator

        return LLMJudgeEvaluator(judge=judge or MockJudge(), thresholds=thresholds)

    if engine == "ragas":
        from rag_forge_evaluator.engines.ragas_evaluator import RagasEvaluator

        return RagasEvaluator(thresholds=thresholds)

    if engine == "deepeval":
        from rag_forge_evaluator.engines.deepeval_evaluator import DeepEvalEvaluator

        return DeepEvalEvaluator(thresholds=thresholds)

    raise ValueError(
        f"Unknown evaluator engine: {engine!r}. "
        "Expected one of: 'llm-judge', 'ragas', 'deepeval'."
    )
```

Create `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py`:

```python
"""RAGAS framework evaluator wrapper.

Requires: pip install rag-forge-evaluator[ragas]
"""

try:
    import ragas  # noqa: F401
except ImportError:
    raise ImportError(
        "RAGAS is not installed. Install with: pip install rag-forge-evaluator[ragas]"
    )

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
)


class RagasEvaluator(EvaluatorInterface):
    """Evaluator using the RAGAS framework.

    Wraps RAGAS v2 metrics for faithfulness, context relevancy,
    answer relevancy, and context recall.
    """

    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self._thresholds = thresholds or {}

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        """Evaluate samples using RAGAS metrics."""
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
        from datasets import Dataset

        data = {
            "question": [s.query for s in samples],
            "answer": [s.response for s in samples],
            "contexts": [s.contexts for s in samples],
            "ground_truth": [s.expected_answer or "" for s in samples],
        }
        dataset = Dataset.from_dict(data)

        result = ragas_evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        default_thresholds = {"faithfulness": 0.85, "answer_relevancy": 0.80, "context_precision": 0.80, "context_recall": 0.70}

        aggregated: list[MetricResult] = []
        for name in metric_names:
            score = float(result.get(name, 0.0))
            threshold = self._thresholds.get(name, default_thresholds.get(name, 0.80))
            aggregated.append(
                MetricResult(name=name, score=round(score, 4), threshold=threshold, passed=score >= threshold)
            )

        overall = sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        return EvaluationResult(
            metrics=aggregated,
            overall_score=round(overall, 4),
            samples_evaluated=len(samples),
            passed=all(m.passed for m in aggregated),
        )

    def supported_metrics(self) -> list[str]:
        return ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
```

Create `packages/evaluator/src/rag_forge_evaluator/engines/deepeval_evaluator.py`:

```python
"""DeepEval framework evaluator wrapper.

Requires: pip install rag-forge-evaluator[deepeval]
"""

try:
    import deepeval  # noqa: F401
except ImportError:
    raise ImportError(
        "DeepEval is not installed. Install with: pip install rag-forge-evaluator[deepeval]"
    )

from rag_forge_evaluator.engine import (
    EvaluationResult,
    EvaluationSample,
    EvaluatorInterface,
    MetricResult,
)


class DeepEvalEvaluator(EvaluatorInterface):
    """Evaluator using the DeepEval framework.

    Wraps DeepEval metrics for faithfulness, contextual relevancy,
    answer relevancy, and hallucination.
    """

    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self._thresholds = thresholds or {}

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult:
        """Evaluate samples using DeepEval metrics."""
        from deepeval import evaluate as deepeval_evaluate
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            ContextualRelevancyMetric,
            FaithfulnessMetric,
            HallucinationMetric,
        )
        from deepeval.test_case import LLMTestCase

        test_cases = [
            LLMTestCase(
                input=s.query,
                actual_output=s.response,
                retrieval_context=s.contexts,
                expected_output=s.expected_answer or "",
            )
            for s in samples
        ]

        metrics = [
            FaithfulnessMetric(threshold=self._thresholds.get("faithfulness", 0.85)),
            ContextualRelevancyMetric(threshold=self._thresholds.get("contextual_relevancy", 0.80)),
            AnswerRelevancyMetric(threshold=self._thresholds.get("answer_relevancy", 0.80)),
            HallucinationMetric(threshold=self._thresholds.get("hallucination", 0.95)),
        ]

        results = deepeval_evaluate(test_cases, metrics)

        metric_names = ["faithfulness", "contextual_relevancy", "answer_relevancy", "hallucination"]
        aggregated: list[MetricResult] = []
        for i, name in enumerate(metric_names):
            score = float(metrics[i].score) if hasattr(metrics[i], "score") else 0.0
            threshold = float(metrics[i].threshold)
            aggregated.append(
                MetricResult(name=name, score=round(score, 4), threshold=threshold, passed=score >= threshold)
            )

        overall = sum(m.score for m in aggregated) / len(aggregated) if aggregated else 0.0
        return EvaluationResult(
            metrics=aggregated,
            overall_score=round(overall, 4),
            samples_evaluated=len(samples),
            passed=all(m.passed for m in aggregated),
        )

    def supported_metrics(self) -> list[str]:
        return ["faithfulness", "contextual_relevancy", "answer_relevancy", "hallucination"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/evaluator && uv run pytest tests/test_evaluator_factory.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/engines/ packages/evaluator/tests/test_evaluator_factory.py
git commit -m "feat(evaluator): add evaluator engine factory with RAGAS and DeepEval wrappers"
```

---

## Task 5: Audit History

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/history.py`
- Test: `packages/evaluator/tests/test_history.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/evaluator/tests/test_history.py`:

```python
"""Tests for audit history tracking."""

import json
import tempfile
from pathlib import Path

from rag_forge_evaluator.history import AuditHistory, AuditHistoryEntry


def _sample_entry(score: float = 0.87) -> AuditHistoryEntry:
    return AuditHistoryEntry(
        timestamp="2026-04-12T10:00:00Z",
        metrics={"faithfulness": score, "context_relevance": 0.82},
        rmm_level=3,
        overall_score=score,
        passed=True,
    )


class TestAuditHistory:
    def test_load_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            history = AuditHistory(Path(tmpdir) / "audit-history.json")
            entries = history.load()
            assert entries == []

    def test_append_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry())
            assert path.exists()

    def test_append_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.85))
            history.append(_sample_entry(0.90))
            entries = history.load()
            assert len(entries) == 2
            assert entries[0].overall_score == 0.85
            assert entries[1].overall_score == 0.90

    def test_get_previous_returns_last(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.80))
            history.append(_sample_entry(0.90))
            prev = history.get_previous()
            assert prev is not None
            assert prev.overall_score == 0.90

    def test_get_previous_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            history = AuditHistory(Path(tmpdir) / "audit-history.json")
            assert history.get_previous() is None

    def test_entry_fields(self) -> None:
        entry = _sample_entry()
        assert entry.timestamp == "2026-04-12T10:00:00Z"
        assert entry.rmm_level == 3
        assert isinstance(entry.metrics, dict)
        assert isinstance(entry.passed, bool)

    def test_compute_trends_improving(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.80))
            prev = history.get_previous()
            current = {"faithfulness": 0.90, "context_relevance": 0.82}
            trends = history.compute_trends(current, prev)
            assert trends["faithfulness"] == "↑"

    def test_compute_trends_declining(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.90))
            prev = history.get_previous()
            current = {"faithfulness": 0.80, "context_relevance": 0.82}
            trends = history.compute_trends(current, prev)
            assert trends["faithfulness"] == "↓"

    def test_compute_trends_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit-history.json"
            history = AuditHistory(path)
            history.append(_sample_entry(0.87))
            prev = history.get_previous()
            current = {"faithfulness": 0.88, "context_relevance": 0.82}
            trends = history.compute_trends(current, prev)
            assert trends["faithfulness"] == "→"

    def test_compute_trends_no_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            history = AuditHistory(Path(tmpdir) / "audit-history.json")
            trends = history.compute_trends({"faithfulness": 0.90}, None)
            assert trends == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/evaluator && uv run pytest tests/test_history.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `packages/evaluator/src/rag_forge_evaluator/history.py`:

```python
"""Audit history tracking for trend analysis."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AuditHistoryEntry:
    """A single historical audit run."""

    timestamp: str
    metrics: dict[str, float]
    rmm_level: int
    overall_score: float
    passed: bool


class AuditHistory:
    """Reads/writes audit-history.json for trend tracking."""

    def __init__(self, history_path: Path) -> None:
        self._path = history_path

    def load(self) -> list[AuditHistoryEntry]:
        """Load previous audit entries. Returns empty list if file doesn't exist."""
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return [AuditHistoryEntry(**entry) for entry in data]

    def append(self, entry: AuditHistoryEntry) -> None:
        """Append a new entry and write back to disk."""
        entries = self.load()
        entries.append(entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([asdict(e) for e in entries], indent=2),
            encoding="utf-8",
        )

    def get_previous(self) -> AuditHistoryEntry | None:
        """Get the most recent previous entry for trend comparison."""
        entries = self.load()
        return entries[-1] if entries else None

    def compute_trends(
        self, current: dict[str, float], previous: AuditHistoryEntry | None
    ) -> dict[str, str]:
        """Compute trend arrows by comparing current vs previous scores.

        Returns ↑ if improved by ≥0.02, ↓ if declined by ≥0.02, → if stable.
        Returns empty dict if no previous data.
        """
        if previous is None:
            return {}

        trends: dict[str, str] = {}
        for metric, score in current.items():
            prev_score = previous.metrics.get(metric)
            if prev_score is None:
                trends[metric] = "→"
            elif score - prev_score >= 0.02:
                trends[metric] = "↑"
            elif prev_score - score >= 0.02:
                trends[metric] = "↓"
            else:
                trends[metric] = "→"
        return trends
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/evaluator && uv run pytest tests/test_history.py -v`
Expected: All 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/history.py packages/evaluator/tests/test_history.py
git commit -m "feat(evaluator): add audit history tracking with trend analysis"
```

---

## Task 6: Radar Chart SVG Generator

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/report/radar.py`
- Test: `packages/evaluator/tests/test_radar_chart.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/evaluator/tests/test_radar_chart.py`:

```python
"""Tests for radar chart SVG generation."""

from rag_forge_evaluator.engine import MetricResult
from rag_forge_evaluator.report.radar import generate_radar_svg


class TestRadarChart:
    def test_generates_svg(self) -> None:
        metrics = [
            MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
            MetricResult(name="context_relevance", score=0.82, threshold=0.80, passed=True),
            MetricResult(name="answer_relevance", score=0.78, threshold=0.80, passed=False),
            MetricResult(name="hallucination", score=0.95, threshold=0.95, passed=True),
        ]
        svg = generate_radar_svg(metrics)
        assert svg.startswith("<svg")
        assert "</svg>" in svg

    def test_contains_metric_labels(self) -> None:
        metrics = [
            MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
            MetricResult(name="context_relevance", score=0.82, threshold=0.80, passed=True),
        ]
        svg = generate_radar_svg(metrics)
        assert "faithfulness" in svg
        assert "context_relevance" in svg

    def test_contains_score_polygon(self) -> None:
        metrics = [
            MetricResult(name="a", score=0.5, threshold=0.5, passed=True),
            MetricResult(name="b", score=0.7, threshold=0.5, passed=True),
            MetricResult(name="c", score=0.9, threshold=0.5, passed=True),
        ]
        svg = generate_radar_svg(metrics)
        assert "polygon" in svg or "path" in svg

    def test_empty_metrics(self) -> None:
        svg = generate_radar_svg([])
        assert "<svg" in svg
        assert "No metrics" in svg

    def test_single_metric(self) -> None:
        metrics = [MetricResult(name="only", score=0.8, threshold=0.5, passed=True)]
        svg = generate_radar_svg(metrics)
        assert "<svg" in svg
        assert "only" in svg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/evaluator && uv run pytest tests/test_radar_chart.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `packages/evaluator/src/rag_forge_evaluator/report/radar.py`:

```python
"""Inline SVG radar chart generator for audit reports."""

import math

from rag_forge_evaluator.engine import MetricResult

_SVG_SIZE = 400
_CENTER = _SVG_SIZE / 2
_RADIUS = 150
_LABEL_OFFSET = 25


def generate_radar_svg(metrics: list[MetricResult]) -> str:
    """Generate an inline SVG radar/spider chart for metric scores.

    Pure Python string construction — no chart libraries needed.
    Each metric gets one axis from center. Score plotted as filled polygon.
    """
    if not metrics:
        return (
            f'<svg width="{_SVG_SIZE}" height="{_SVG_SIZE}" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="{_CENTER}" y="{_CENTER}" text-anchor="middle" fill="#999" '
            f'font-family="sans-serif" font-size="14">No metrics to display</text></svg>'
        )

    n = len(metrics)
    angle_step = 2 * math.pi / n

    lines: list[str] = [
        f'<svg width="{_SVG_SIZE}" height="{_SVG_SIZE}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{_SVG_SIZE}" height="{_SVG_SIZE}" fill="white"/>',
    ]

    # Draw grid circles at 25%, 50%, 75%, 100%
    for pct in (0.25, 0.5, 0.75, 1.0):
        r = _RADIUS * pct
        lines.append(
            f'<circle cx="{_CENTER}" cy="{_CENTER}" r="{r:.1f}" '
            f'fill="none" stroke="#e0e0e0" stroke-width="1"/>'
        )

    # Draw axis lines and labels
    axis_points: list[tuple[float, float]] = []
    for i, m in enumerate(metrics):
        angle = -math.pi / 2 + i * angle_step
        x = _CENTER + _RADIUS * math.cos(angle)
        y = _CENTER + _RADIUS * math.sin(angle)
        axis_points.append((x, y))

        lines.append(
            f'<line x1="{_CENTER}" y1="{_CENTER}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="#ccc" stroke-width="1"/>'
        )

        lx = _CENTER + (_RADIUS + _LABEL_OFFSET) * math.cos(angle)
        ly = _CENTER + (_RADIUS + _LABEL_OFFSET) * math.sin(angle)
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"

        lines.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'dominant-baseline="central" font-family="sans-serif" font-size="11" '
            f'fill="#555">{m.name}</text>'
        )

    # Draw threshold polygon
    threshold_points: list[str] = []
    for i, m in enumerate(metrics):
        angle = -math.pi / 2 + i * angle_step
        r = _RADIUS * min(m.threshold, 1.0)
        x = _CENTER + r * math.cos(angle)
        y = _CENTER + r * math.sin(angle)
        threshold_points.append(f"{x:.1f},{y:.1f}")

    lines.append(
        f'<polygon points="{" ".join(threshold_points)}" '
        f'fill="rgba(255,193,7,0.1)" stroke="#ffc107" stroke-width="1" stroke-dasharray="4,4"/>'
    )

    # Draw score polygon
    score_points: list[str] = []
    for i, m in enumerate(metrics):
        angle = -math.pi / 2 + i * angle_step
        r = _RADIUS * min(m.score, 1.0)
        x = _CENTER + r * math.cos(angle)
        y = _CENTER + r * math.sin(angle)
        score_points.append(f"{x:.1f},{y:.1f}")

    lines.append(
        f'<polygon points="{" ".join(score_points)}" '
        f'fill="rgba(40,167,69,0.2)" stroke="#28a745" stroke-width="2"/>'
    )

    # Draw score dots
    for i, m in enumerate(metrics):
        angle = -math.pi / 2 + i * angle_step
        r = _RADIUS * min(m.score, 1.0)
        x = _CENTER + r * math.cos(angle)
        y = _CENTER + r * math.sin(angle)
        color = "#28a745" if m.passed else "#dc3545"
        lines.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>'
        )

    lines.append("</svg>")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/evaluator && uv run pytest tests/test_radar_chart.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/report/radar.py packages/evaluator/tests/test_radar_chart.py
git commit -m "feat(evaluator): add inline SVG radar chart generator"
```

---

## Task 7: Enhanced Report Generator (JSON + HTML)

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/report/generator.py`
- Test: `packages/evaluator/tests/test_json_report.py`
- Test: `packages/evaluator/tests/test_enhanced_report.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/evaluator/tests/test_json_report.py`:

```python
"""Tests for JSON report output."""

import json
import tempfile
from pathlib import Path

from rag_forge_evaluator.engine import EvaluationResult, MetricResult, SampleResult
from rag_forge_evaluator.maturity import RMMLevel
from rag_forge_evaluator.report.generator import ReportGenerator


class TestJsonReport:
    def test_generates_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True)],
                overall_score=0.90,
                samples_evaluated=5,
                passed=True,
            )
            path = gen.generate_json(result, RMMLevel.TRUST)
            assert path.exists()
            assert path.suffix == ".json"

    def test_json_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[
                    MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
                    MetricResult(name="context_relevance", score=0.82, threshold=0.80, passed=True),
                ],
                overall_score=0.86,
                samples_evaluated=10,
                passed=True,
            )
            path = gen.generate_json(result, RMMLevel.TRUST)
            data = json.loads(path.read_text(encoding="utf-8"))

            assert "timestamp" in data
            assert data["overall_score"] == 0.86
            assert data["passed"] is True
            assert data["rmm_level"] == 3
            assert data["samples_evaluated"] == 10
            assert "faithfulness" in data["metrics"]
            assert data["metrics"]["faithfulness"]["score"] == 0.90

    def test_json_includes_worst_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            sample_results = [
                SampleResult(query="bad query", response="bad response", metrics={"faithfulness": 0.3}, worst_metric="faithfulness", root_cause="generation"),
            ]
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.3, threshold=0.85, passed=False)],
                overall_score=0.3,
                samples_evaluated=1,
                passed=False,
                sample_results=sample_results,
            )
            path = gen.generate_json(result, RMMLevel.NAIVE, sample_results=sample_results)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data["worst_samples"]) == 1
            assert data["worst_samples"][0]["root_cause"] == "generation"
```

Create `packages/evaluator/tests/test_enhanced_report.py`:

```python
"""Tests for enhanced HTML report."""

import tempfile

from rag_forge_evaluator.engine import EvaluationResult, MetricResult, SampleResult
from rag_forge_evaluator.history import AuditHistoryEntry
from rag_forge_evaluator.maturity import RMMLevel
from rag_forge_evaluator.report.generator import ReportGenerator


class TestEnhancedReport:
    def test_html_contains_radar_chart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[
                    MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True),
                    MetricResult(name="context_relevance", score=0.82, threshold=0.80, passed=True),
                ],
                overall_score=0.86,
                samples_evaluated=5,
                passed=True,
            )
            path = gen.generate_html(result, RMMLevel.TRUST)
            html = path.read_text(encoding="utf-8")
            assert "<svg" in html
            assert "polygon" in html

    def test_html_contains_trend_arrows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True)],
                overall_score=0.90,
                samples_evaluated=5,
                passed=True,
            )
            trends = {"faithfulness": "↑"}
            path = gen.generate_html(result, RMMLevel.TRUST, trends=trends)
            html = path.read_text(encoding="utf-8")
            assert "↑" in html

    def test_html_contains_per_sample_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            sample_results = [
                SampleResult(query="What is Python?", response="A language", metrics={"faithfulness": 0.90}, worst_metric="faithfulness", root_cause="none"),
            ]
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True)],
                overall_score=0.90,
                samples_evaluated=1,
                passed=True,
                sample_results=sample_results,
            )
            path = gen.generate_html(result, RMMLevel.TRUST, sample_results=sample_results)
            html = path.read_text(encoding="utf-8")
            assert "What is Python?" in html
            assert "Per-Sample" in html or "per-sample" in html or "Sample" in html

    def test_html_no_trends_without_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator(output_dir=tmpdir)
            result = EvaluationResult(
                metrics=[MetricResult(name="faithfulness", score=0.90, threshold=0.85, passed=True)],
                overall_score=0.90,
                samples_evaluated=5,
                passed=True,
            )
            path = gen.generate_html(result, RMMLevel.TRUST)
            html = path.read_text(encoding="utf-8")
            assert "↑" not in html
            assert "↓" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/evaluator && uv run pytest tests/test_json_report.py tests/test_enhanced_report.py -v`
Expected: FAIL — methods don't exist yet.

- [ ] **Step 3: Update the report generator**

Replace the full contents of `packages/evaluator/src/rag_forge_evaluator/report/generator.py`:

```python
"""HTML and JSON audit report generator."""

import json
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rag_forge_evaluator.engine import EvaluationResult, MetricResult, SampleResult
from rag_forge_evaluator.maturity import RMM_CRITERIA, RMMLevel
from rag_forge_evaluator.report.radar import generate_radar_svg

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


def _get_worst_samples(
    sample_results: list[SampleResult], top_n: int = 3
) -> list[SampleResult]:
    """Get the worst-performing samples sorted by lowest metric score."""
    if not sample_results:
        return []
    scored = [
        (sr, min(sr.metrics.values()) if sr.metrics else 0.0)
        for sr in sample_results
    ]
    scored.sort(key=lambda x: x[1])
    return [sr for sr, _ in scored[:top_n]]


class ReportGenerator:
    """Generates standalone HTML and JSON audit reports."""

    def __init__(self, output_dir: str | Path = "./reports") -> None:
        self.output_dir = Path(output_dir)

    def generate_html(
        self,
        result: EvaluationResult,
        rmm_level: RMMLevel,
        trends: dict[str, str] | None = None,
        sample_results: list[SampleResult] | None = None,
    ) -> Path:
        """Generate an enhanced standalone HTML report."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)
        template = env.get_template("audit_report.html.j2")

        rmm_name = next(
            (c.name for c in RMM_CRITERIA if c.level == rmm_level), "Unknown"
        )

        radar_svg = generate_radar_svg(result.metrics)
        worst_samples = _get_worst_samples(sample_results or [])

        html = template.render(
            timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC"),
            rmm_level=int(rmm_level),
            rmm_name=rmm_name,
            overall_score=result.overall_score,
            passed=result.passed,
            samples_evaluated=result.samples_evaluated,
            metrics=result.metrics,
            recommendations=_generate_recommendations(result),
            radar_svg=radar_svg,
            trends=trends or {},
            sample_results=sample_results or [],
            worst_samples=worst_samples,
        )

        output_path = self.output_dir / "audit-report.html"
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def generate_json(
        self,
        result: EvaluationResult,
        rmm_level: RMMLevel,
        sample_results: list[SampleResult] | None = None,
    ) -> Path:
        """Write machine-readable audit-report.json alongside the HTML."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        rmm_name = next(
            (c.name for c in RMM_CRITERIA if c.level == rmm_level), "Unknown"
        )

        worst = _get_worst_samples(sample_results or [])

        data = {
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "overall_score": result.overall_score,
            "passed": result.passed,
            "rmm_level": int(rmm_level),
            "rmm_name": rmm_name,
            "samples_evaluated": result.samples_evaluated,
            "metrics": {
                m.name: {"score": m.score, "threshold": m.threshold, "passed": m.passed}
                for m in result.metrics
            },
            "worst_samples": [
                {
                    "query": s.query,
                    "worst_metric": s.worst_metric,
                    "score": min(s.metrics.values()) if s.metrics else 0.0,
                    "root_cause": s.root_cause,
                }
                for s in worst
            ],
        }

        output_path = self.output_dir / "audit-report.json"
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return output_path
```

- [ ] **Step 4: Update the HTML template**

Replace the full contents of `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2` with the enhanced version that includes radar chart, trends, per-sample breakdown, and visual polish. The template should:

- Render `{{ radar_svg | safe }}` below the summary cards
- Add a "Trend" column to the metrics table showing `{{ trends.get(m.name, "") }}`
- Add a "Per-Sample Breakdown" section with collapsible `<details>` tags listing each sample's metrics
- Add a "Worst Queries" highlighted box showing top 3 worst samples with root cause badges
- Improve visual styling with gradients, card shadows, and better typography

The full template content is provided in the implementation step — the engineer should write it with the template variables: `radar_svg`, `trends`, `sample_results`, `worst_samples` alongside all existing variables.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/evaluator && uv run pytest tests/test_json_report.py tests/test_enhanced_report.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 6: Run existing report tests**

Run: `cd packages/evaluator && uv run pytest tests/test_report.py -v`
Expected: All existing tests PASS (backward compatible — new params are optional).

- [ ] **Step 7: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/report/ packages/evaluator/tests/test_json_report.py packages/evaluator/tests/test_enhanced_report.py
git commit -m "feat(evaluator): add JSON report output and enhanced HTML with radar chart and trends"
```

---

## Task 8: Update AuditOrchestrator

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/audit.py`

- [ ] **Step 1: Update AuditOrchestrator**

Replace the full contents of `packages/evaluator/src/rag_forge_evaluator/audit.py`:

```python
"""Audit orchestrator: coordinates evaluation, history, and report generation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rag_forge_evaluator.engine import EvaluationResult
from rag_forge_evaluator.engines import create_evaluator
from rag_forge_evaluator.history import AuditHistory, AuditHistoryEntry
from rag_forge_evaluator.input_loader import InputLoader
from rag_forge_evaluator.judge.base import JudgeProvider
from rag_forge_evaluator.judge.mock_judge import MockJudge
from rag_forge_evaluator.maturity import RMMLevel, RMMScorer
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
    evaluator_engine: str = "llm-judge"


@dataclass
class AuditReport:
    """Complete audit report with evaluation results and RMM scoring."""

    evaluation: EvaluationResult
    rmm_level: RMMLevel
    report_path: Path
    json_report_path: Path
    samples_evaluated: int


def _create_judge(model: str | None) -> JudgeProvider:
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
    """Orchestrates the full audit pipeline."""

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

        # 2. Create evaluator via factory
        judge = _create_judge(self.config.judge_model)
        evaluator = create_evaluator(
            self.config.evaluator_engine,
            judge=judge,
            thresholds=self.config.thresholds,
        )

        # 3. Run evaluation
        evaluation = evaluator.evaluate(samples)

        # 4. Score against RMM
        metric_map = {m.name: m.score for m in evaluation.metrics}
        rmm_level = RMMScorer().assess(metric_map)

        # 5. Load history and compute trends
        history = AuditHistory(self.config.output_dir / "audit-history.json")
        previous = history.get_previous()
        trends = history.compute_trends(metric_map, previous)

        # 6. Generate reports
        generator = ReportGenerator(output_dir=self.config.output_dir)
        report_path = generator.generate_html(
            evaluation, rmm_level,
            trends=trends,
            sample_results=evaluation.sample_results,
        )
        json_report_path = generator.generate_json(
            evaluation, rmm_level,
            sample_results=evaluation.sample_results,
        )

        # 7. Append to history
        history.append(AuditHistoryEntry(
            timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            metrics=metric_map,
            rmm_level=int(rmm_level),
            overall_score=evaluation.overall_score,
            passed=evaluation.passed,
        ))

        return AuditReport(
            evaluation=evaluation,
            rmm_level=rmm_level,
            report_path=report_path,
            json_report_path=json_report_path,
            samples_evaluated=evaluation.samples_evaluated,
        )
```

- [ ] **Step 2: Run existing audit tests**

Run: `cd packages/evaluator && uv run pytest tests/test_audit.py -v`
Expected: Tests may need minor updates for the new `json_report_path` field on `AuditReport`. Fix any that fail.

- [ ] **Step 3: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/audit.py
git commit -m "feat(evaluator): integrate engine factory, history, and JSON output into AuditOrchestrator"
```

---

## Task 9: Update CLIs

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/cli.py`
- Modify: `packages/cli/src/commands/audit.ts`

- [ ] **Step 1: Update Python evaluator CLI**

Add `--evaluator` argument. Update `cmd_audit` to pass `evaluator_engine` to `AuditConfig`. Add `json_report_path` to stdout output.

In `cli.py`, add to the `audit_parser`:
```python
    audit_parser.add_argument(
        "--evaluator", default="llm-judge",
        help="Evaluator engine: llm-judge | ragas | deepeval",
    )
```

In `cmd_audit`, update `AuditConfig` construction:
```python
    config = AuditConfig(
        ...
        evaluator_engine=args.evaluator,
    )
```

Add to the output dict:
```python
        "json_report_path": str(report.json_report_path),
        "evaluator_engine": config.evaluator_engine,
```

- [ ] **Step 2: Update TypeScript audit CLI**

In `audit.ts`, add option:
```typescript
    .option("--evaluator <engine>", "Evaluator engine: llm-judge | ragas | deepeval", "llm-judge")
```

Add to options type: `evaluator: string;`

Add to args: `args.push("--evaluator", options.evaluator);`

Update `AuditResult` interface to include `json_report_path: string` and `evaluator_engine: string`.

After displaying metrics, add:
```typescript
          logger.info(`Evaluator: ${output.evaluator_engine}`);
```

- [ ] **Step 3: Build TypeScript**

Run: `cd packages/cli && pnpm run build && npx tsc --noEmit`
Expected: Build and typecheck succeed.

- [ ] **Step 4: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/cli.py packages/cli/src/commands/audit.ts
git commit -m "feat(cli): add --evaluator flag to audit command"
```

---

## Task 10: Activate CI/CD Gate Workflow

**Files:**
- Modify: `.github/workflows/rag-audit.yml`

- [ ] **Step 1: Replace the placeholder workflow**

Replace the full contents of `.github/workflows/rag-audit.yml`:

```yaml
name: RAG Audit Gate

on:
  pull_request:
    branches: [main]
    paths:
      - "packages/core/src/**"
      - "packages/evaluator/src/**"
      - "eval/**"
      - "rag-forge.config.*"

jobs:
  audit:
    name: RAG Quality Gate
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Setup Python
        run: uv python install 3.11

      - name: Install dependencies
        run: |
          pnpm install --frozen-lockfile
          uv sync --all-packages

      - name: Build CLI
        run: pnpm exec turbo run build

      - name: Run RAG Audit
        run: |
          uv run python -m rag_forge_evaluator.cli audit \
            --golden-set eval/golden_set.json \
            --judge mock \
            --output ./reports \
            --evaluator llm-judge

      - name: Check gate metric
        run: |
          METRIC="faithfulness"
          THRESHOLD="0.85"
          SCORE=$(jq -r ".metrics.${METRIC}.score" reports/audit-report.json)
          echo "Gate metric: ${METRIC}, Score: ${SCORE}, Threshold: ${THRESHOLD}"
          if (( $(echo "$SCORE < $THRESHOLD" | bc -l) )); then
            echo "::error::${METRIC} score (${SCORE}) is below threshold (${THRESHOLD})"
            exit 1
          fi

      - name: Upload audit report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: rag-audit-report
          path: reports/
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/rag-audit.yml
git commit -m "feat(ci): activate RAG audit gate workflow with artifact upload"
```

---

## Task 11: Integration Test — Full Audit with History

**Files:**
- Create: `packages/evaluator/tests/test_audit_enhanced_integration.py`

- [ ] **Step 1: Write the integration test**

Create `packages/evaluator/tests/test_audit_enhanced_integration.py`:

```python
"""Integration test: full audit with history and enhanced reports."""

import json
import tempfile
from pathlib import Path

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator


def _create_test_jsonl(path: Path) -> None:
    """Create a small test JSONL file."""
    samples = [
        {"query": "What is Python?", "contexts": ["Python is a programming language."], "response": "Python is a programming language."},
        {"query": "What is Rust?", "contexts": ["Rust is a systems language."], "response": "Rust provides memory safety."},
        {"query": "What is JavaScript?", "contexts": ["JavaScript runs in browsers."], "response": "JavaScript powers web apps."},
    ]
    path.write_text("\n".join(json.dumps(s) for s in samples), encoding="utf-8")


class TestAuditEnhancedIntegration:
    def test_full_audit_produces_html_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)

            config = AuditConfig(input_path=jsonl, output_dir=tmp / "reports")
            report = AuditOrchestrator(config).run()

            assert report.report_path.exists()
            assert report.json_report_path.exists()
            assert report.report_path.suffix == ".html"
            assert report.json_report_path.suffix == ".json"

    def test_json_report_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)

            config = AuditConfig(input_path=jsonl, output_dir=tmp / "reports")
            report = AuditOrchestrator(config).run()

            data = json.loads(report.json_report_path.read_text(encoding="utf-8"))
            assert "metrics" in data
            assert "faithfulness" in data["metrics"]
            assert data["samples_evaluated"] == 3

    def test_history_appended_after_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)
            output_dir = tmp / "reports"

            config = AuditConfig(input_path=jsonl, output_dir=output_dir)
            AuditOrchestrator(config).run()

            history_path = output_dir / "audit-history.json"
            assert history_path.exists()
            history = json.loads(history_path.read_text(encoding="utf-8"))
            assert len(history) == 1

    def test_second_run_has_trends(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)
            output_dir = tmp / "reports"

            config = AuditConfig(input_path=jsonl, output_dir=output_dir)
            AuditOrchestrator(config).run()
            report2 = AuditOrchestrator(config).run()

            history_path = output_dir / "audit-history.json"
            history = json.loads(history_path.read_text(encoding="utf-8"))
            assert len(history) == 2

            html = report2.report_path.read_text(encoding="utf-8")
            assert "<svg" in html

    def test_html_contains_per_sample_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)

            config = AuditConfig(input_path=jsonl, output_dir=tmp / "reports")
            report = AuditOrchestrator(config).run()

            html = report.report_path.read_text(encoding="utf-8")
            assert "What is Python?" in html
```

- [ ] **Step 2: Run the integration test**

Run: `cd packages/evaluator && uv run pytest tests/test_audit_enhanced_integration.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/evaluator/tests/test_audit_enhanced_integration.py
git commit -m "test(evaluator): add enhanced audit integration tests with history"
```

---

## Task 12: Run Full Test Suite and Lint

- [ ] **Step 1: Run all Python tests**

Run: `cd packages/evaluator && uv run pytest -v`
Expected: ALL tests pass.

Run: `cd packages/core && uv run pytest -v`
Expected: ALL tests pass.

- [ ] **Step 2: Run Python linter**

Run: `uv run ruff check .`
Expected: No errors. Fix any that appear.

- [ ] **Step 3: Run Python type checker**

Run: `uv run mypy packages/evaluator/src packages/core/src`
Expected: No errors. Fix any that appear.

- [ ] **Step 4: Build TypeScript**

Run: `pnpm run build`
Expected: Build succeeds.

- [ ] **Step 5: Run TypeScript lint and typecheck**

Run: `pnpm run lint && pnpm run typecheck`
Expected: No errors.

- [ ] **Step 6: Fix any issues, then commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors from Phase 2C implementation"
```

- [ ] **Step 7: Push**

```bash
git push
```
