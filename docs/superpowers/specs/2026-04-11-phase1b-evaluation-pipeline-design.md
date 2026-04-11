# Phase 1B: Evaluation Pipeline Design Spec

## Context

RAG-Forge's killer feature is `rag-forge audit` — instant pipeline health assessments with scored evaluation reports. Phase 1A built the data pipeline (parse, chunk, embed, store). Phase 1B builds the evaluation pipeline that scores RAG output quality and produces human-readable reports.

The Phase 1 exit criteria requires: `rag-forge audit --golden-set qa.json` produces a scored evaluation report. This spec delivers that.

## Scope

**In scope:** JSONL telemetry loader, golden set loader, LLM-as-Judge evaluation engine (Claude + GPT-4o), four metrics (faithfulness, context relevance, answer relevance, hallucination rate), RMM scoring logic, audit orchestrator, HTML report generator, CLI `audit` command wiring, Python CLI `audit` subcommand.

**Out of scope:** RAGAS integration, DeepEval integration, PDF report export (Playwright), radar charts, trend arrows, cost analysis. These are Phase 2/3 features.

## Architecture

Metric-per-class with evaluator orchestrator. Each metric is its own class behind a `MetricEvaluator` protocol. The `LLMJudgeEvaluator` implements the existing `EvaluatorInterface` ABC and delegates to individual metrics via a `JudgeProvider` abstraction (Claude or GPT-4o).

```
rag-forge audit --input telemetry.jsonl
       │
       ▼
  TypeScript CLI (audit command)
       │
       ▼ (Python bridge: uv run python -m rag_forge_core.cli)
       │
  Python CLI audit subcommand (in evaluator package)
       │
       ▼
  AuditOrchestrator.run()
       │
       ├─ 1. InputLoader.load_jsonl(path) or InputLoader.load_golden_set(path)
       │      └─ Returns: list[EvaluationSample]
       │
       ├─ 2. LLMJudgeEvaluator.evaluate(samples)
       │      ├─ FaithfulnessMetric.evaluate_sample(sample, judge)
       │      ├─ ContextRelevanceMetric.evaluate_sample(sample, judge)
       │      └─ AnswerRelevanceMetric.evaluate_sample(sample, judge)
       │            └─ JudgeProvider (ClaudeJudge or OpenAIJudge)
       │      └─ Returns: EvaluationResult
       │
       ├─ 3. RMMScorer.assess(metrics)
       │      └─ Returns: RMMLevel
       │
       └─ 4. ReportGenerator.generate_html(evaluation, rmm_level)
              └─ Returns: Path to audit-report.html
```

## Components

### 1. Input Loading Module

**Location:** `packages/evaluator/src/rag_forge_evaluator/input_loader.py`

Two static methods that both produce `list[EvaluationSample]` (the existing dataclass from engine.py):

**`load_jsonl(path: Path) -> list[EvaluationSample]`**
- Reads a `.jsonl` file line by line
- Each line is JSON: `{"query": "...", "contexts": ["..."], "response": "..."}`
- Required fields: `query`, `contexts`, `response`
- Optional fields: `expected_answer`, `chunk_ids`, `latency_ms`, `model_used`
- Skips malformed lines with a warning (logged, not fatal)
- Returns list of `EvaluationSample`

**`load_golden_set(path: Path) -> list[EvaluationSample]`**
- Reads a JSON array of golden set entries
- Maps `GoldenSetEntry` fields to `EvaluationSample` fields
- For golden set, `contexts` defaults to empty list and `response` defaults to empty string (the evaluator handles this by checking if response is present)
- Validates schema using the existing `GoldenSetEntry` dataclass

**`GoldenSet.load()` enhancement** — the existing stub gets real JSON loading logic with pydantic validation.

### 2. JudgeProvider Abstraction

**Location:** `packages/evaluator/src/rag_forge_evaluator/judge/`

**Protocol:**
```python
class JudgeProvider(Protocol):
    def judge(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt to the LLM judge and return the response text."""
        ...
    def model_name(self) -> str: ...
```

Takes separate `system_prompt` and `user_prompt` for proper LLM structuring.

**Implementations:**

| File | Class | SDK | API Key Env Var | Notes |
|------|-------|-----|-----------------|-------|
| `claude_judge.py` | `ClaudeJudge` | `anthropic` | `ANTHROPIC_API_KEY` | Uses Claude Sonnet by default. Configurable model. |
| `openai_judge.py` | `OpenAIJudge` | `openai` | `OPENAI_API_KEY` | Uses GPT-4o by default. OpenAI SDK already installed. |
| `mock_judge.py` | `MockJudge` | None | None | Returns deterministic JSON scores for testing. Always returns configurable fixed scores. |

### 3. Metric Evaluators

**Location:** `packages/evaluator/src/rag_forge_evaluator/metrics/`

**Protocol:**
```python
class MetricEvaluator(Protocol):
    def name(self) -> str: ...
    def evaluate_sample(self, sample: EvaluationSample, judge: JudgeProvider) -> MetricResult: ...
    def default_threshold(self) -> float: ...
```

**Four implementations:**

#### FaithfulnessMetric
- **What it measures:** Is the response grounded in the retrieved contexts?
- **Prompt strategy:** System prompt instructs the judge to identify factual claims in the response, then check each claim against the provided contexts. Judge returns JSON: `{"claims": [{"text": "...", "supported": true/false}], "score": 0.0-1.0}`
- **Score:** Proportion of claims supported by context (0.0 to 1.0)
- **Default threshold:** 0.85 (the CI gate default from PRD)

#### ContextRelevanceMetric
- **What it measures:** Are the retrieved chunks relevant to the query?
- **Prompt strategy:** System prompt instructs the judge to rate each context chunk's relevance to the query on a 1-5 scale. Judge returns JSON: `{"ratings": [{"chunk_index": 0, "score": 4, "reason": "..."}], "mean_score": 0.0-1.0}`
- **Score:** Mean rating normalized to 0.0-1.0 (rating / 5)
- **Default threshold:** 0.80

#### AnswerRelevanceMetric
- **What it measures:** Does the response address the question asked?
- **Prompt strategy:** System prompt instructs the judge to score the response on completeness (does it address all parts of the query?), correctness (are the facts right?), and coherence (is it well-structured?). Judge returns JSON: `{"completeness": 4, "correctness": 5, "coherence": 4, "overall_score": 0.0-1.0}`
- **Score:** Normalized overall (0.0 to 1.0)
- **Default threshold:** 0.80

#### HallucinationMetric
- **What it measures:** What percentage of claims in the response lack source support?
- **Prompt strategy:** System prompt instructs the judge to extract all factual claims from the response, then for each claim determine if it is supported by any provided context. Judge returns JSON: `{"claims": [{"text": "...", "supported": true/false, "source_chunk": 0}], "unsupported_count": 2, "total_claims": 10, "hallucination_rate": 0.2}`
- **Score:** `1.0 - hallucination_rate` (inverted so higher = better, consistent with other metrics)
- **Default threshold:** 0.95 (meaning max 5% hallucination rate, per PRD)

**Error handling:** If the judge returns invalid JSON or the LLM call fails, the metric returns a `MetricResult` with `score=0.0`, `passed=False`, and `details` explaining the failure. Evaluation continues with remaining samples.

### 4. LLMJudgeEvaluator

**Location:** `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py`

Implements the existing `EvaluatorInterface` ABC:

```python
class LLMJudgeEvaluator(EvaluatorInterface):
    def __init__(self, judge: JudgeProvider, metrics: list[MetricEvaluator] | None = None,
                 thresholds: dict[str, float] | None = None) -> None: ...
    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult: ...
    def supported_metrics(self) -> list[str]: ...
```

- If no metrics provided, defaults to all four (faithfulness, context_relevance, answer_relevance, hallucination)
- Iterates all samples × all metrics
- Per-metric aggregation: mean score across all samples for that metric
- Overall score: mean of all per-metric means
- `passed`: True only if ALL metrics pass their thresholds
- Custom thresholds override metric defaults

### 5. RMM Scorer Enhancement

**Location:** `packages/evaluator/src/rag_forge_evaluator/maturity.py` (modify existing)

The stub `assess()` gets real logic:
- Takes `dict[str, float]` mapping metric names to scores
- For Phase 1, only checks RMM-0 through RMM-3 (higher levels require caching, RBAC, etc.)
- Logic: Walk from RMM-0 upward. Check if each level's requirements are met:
  - **RMM-0 (Naive):** Always passes (basic retrieval works)
  - **RMM-1 (Recall):** Requires `recall_at_k >= 0.70` (not yet available in Phase 1, so skip)
  - **RMM-2 (Precision):** Requires reranker metrics (skip for Phase 1)
  - **RMM-3 (Trust):** Requires `faithfulness >= 0.85` AND `context_relevance >= 0.80`
- Returns the highest passing level
- Metrics not present in the dict are treated as "not evaluated" (don't block progression for metrics that weren't run, but cap at levels that require them)

### 6. Audit Orchestrator Enhancement

**Location:** `packages/evaluator/src/rag_forge_evaluator/audit.py` (modify existing)

```python
@dataclass
class AuditReport:
    evaluation: EvaluationResult
    rmm_level: RMMLevel
    report_path: Path
    samples_evaluated: int

class AuditOrchestrator:
    def __init__(self, config: AuditConfig) -> None: ...
    def run(self) -> AuditReport: ...
```

Pipeline:
1. Load input based on config (JSONL or golden set)
2. Create JudgeProvider based on config (Claude, OpenAI, or mock)
3. Create LLMJudgeEvaluator with judge + default metrics
4. Run evaluation
5. Score against RMM
6. Generate HTML report
7. Return AuditReport

### 7. HTML Report Generator Enhancement

**Location:** `packages/evaluator/src/rag_forge_evaluator/report/generator.py` (modify existing)

Jinja2-based template rendering. Single standalone HTML file with inline CSS.

**Report structure:**
- Header: "RAG-Forge Audit Report" + timestamp + pipeline name
- RMM badge: "RMM-3: Better Trust" with color (green/yellow/red based on level)
- Summary: overall score, pass/fail, samples evaluated
- Metrics table: name | score | threshold | status (PASS/FAIL)
- Per-sample breakdown (collapsible): query, response snippet (truncated to 200 chars), per-metric scores
- Recommendations: bulleted list based on which metrics failed and by how much
- Footer: "Generated by RAG-Forge v0.1.0"

**Template location:** `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2`

### 8. CLI Integration

**Modify:** `packages/cli/src/commands/audit.ts` — wire to Python bridge
**Add:** `audit` subcommand to `packages/evaluator/src/rag_forge_evaluator/cli.py` (new Python CLI for evaluator package, similar to core's cli.py)
**Modify:** `packages/cli/src/commands/audit.ts` — call Python bridge with evaluator module

The TypeScript audit command calls: `uv run python -m rag_forge_evaluator.cli audit --input <file> --judge <model> --config-json <json>`

## Dependencies to Add

**`packages/evaluator/pyproject.toml`:**
```toml
dependencies = [
    "pydantic>=2.0",
    "jinja2>=3.1",
    "anthropic>=0.30",
    "openai>=1.30",
]
```

Note: `openai` is already in `packages/core`. Since evaluator is a separate workspace member, it needs its own dependency declaration.

## Files to Create/Modify

### New Files (18)
- `packages/evaluator/src/rag_forge_evaluator/input_loader.py`
- `packages/evaluator/src/rag_forge_evaluator/judge/__init__.py`
- `packages/evaluator/src/rag_forge_evaluator/judge/base.py`
- `packages/evaluator/src/rag_forge_evaluator/judge/claude_judge.py`
- `packages/evaluator/src/rag_forge_evaluator/judge/openai_judge.py`
- `packages/evaluator/src/rag_forge_evaluator/judge/mock_judge.py`
- `packages/evaluator/src/rag_forge_evaluator/metrics/base.py`
- `packages/evaluator/src/rag_forge_evaluator/metrics/faithfulness.py`
- `packages/evaluator/src/rag_forge_evaluator/metrics/context_relevance.py`
- `packages/evaluator/src/rag_forge_evaluator/metrics/answer_relevance.py`
- `packages/evaluator/src/rag_forge_evaluator/metrics/hallucination.py`
- `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py`
- `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2`
- `packages/evaluator/src/rag_forge_evaluator/cli.py`
- `packages/evaluator/tests/test_input_loader.py`
- `packages/evaluator/tests/test_metrics.py`
- `packages/evaluator/tests/test_audit.py`
- `packages/evaluator/tests/test_report.py`

### Modified Files (6)
- `packages/evaluator/pyproject.toml` (add anthropic, openai deps)
- `packages/evaluator/src/rag_forge_evaluator/golden_set.py` (real load logic)
- `packages/evaluator/src/rag_forge_evaluator/maturity.py` (real assess logic)
- `packages/evaluator/src/rag_forge_evaluator/audit.py` (real orchestration)
- `packages/evaluator/src/rag_forge_evaluator/report/generator.py` (Jinja2 template)
- `packages/cli/src/commands/audit.ts` (wire to Python bridge)

## Testing Strategy

- **Unit tests:** MockJudge returns deterministic scores. All metric tests use MockJudge — no external API calls.
- **Input loader tests:** Create temp JSONL and JSON files, verify parsing.
- **Metric tests:** Feed known samples to each metric via MockJudge, verify scores and pass/fail.
- **Audit integration test:** Full pipeline with MockJudge: load JSONL → evaluate → score RMM → generate HTML → verify report file exists and contains expected content.
- **Report test:** Verify HTML output contains metric names, scores, RMM badge, and no Jinja2 template errors.

## Verification

After implementation:
1. `uv run pytest packages/evaluator/tests/ -v` — all tests pass
2. `uv run ruff check .` — zero lint errors
3. `uv run mypy packages/evaluator/src` — zero type errors
4. `pnpm run build` — CLI builds
5. Manual test: create a sample `.jsonl` with 3 entries, run `rag-forge audit --input sample.jsonl --judge mock`, verify HTML report generated
