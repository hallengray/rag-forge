# Phase 2C: Evaluation Enhancements + CI/CD Gate Design Spec

## Context

RAG-Forge Phase 2B delivered the security module. Phase 2C upgrades the evaluation engine with optional RAGAS/DeepEval metric providers, a Lighthouse-quality HTML report with radar charts, per-sample breakdown, trend tracking, and a CI/CD gate workflow that blocks merges when quality drops.

## Scope

**In scope:**
- `RagasEvaluator` and `DeepEvalEvaluator` as optional evaluator engines (via `--evaluator` flag)
- Enhanced HTML report: inline SVG radar chart, per-sample breakdown with worst-query highlighting, trend arrows from historical data, root cause hints (retrieval vs. generation failure), cost analysis section
- Audit history JSON sidecar (`audit-history.json`) for trend tracking
- Machine-readable `audit-report.json` output alongside HTML
- Activated `.github/workflows/rag-audit.yml` with artifact upload and gate metric check
- Updated CLI flags for evaluator selection and JSON output

**Out of scope:** PDF export via Playwright (Phase 3), drift detection (Phase 4), golden set management commands (Phase 4), custom metric plugins.

## Architecture

The existing `EvaluatorInterface` ABC is the extension point. We add two new implementations (`RagasEvaluator`, `DeepEvalEvaluator`) as optional-dependency alternatives to the existing `LLMJudgeEvaluator`. The `AuditOrchestrator` selects the evaluator based on a config flag. The report generator is enhanced with new template sections. History tracking is a simple JSON append/read cycle.

```
rag-forge audit --golden-set eval/golden_set.json --evaluator llm-judge
       │
       ▼
  AuditOrchestrator.run()
       │
       ├─ 1. Load samples (InputLoader)
       │
       ├─ 2. Select evaluator
       │      ├─ llm-judge (default) → LLMJudgeEvaluator
       │      ├─ ragas → RagasEvaluator (optional dep)
       │      └─ deepeval → DeepEvalEvaluator (optional dep)
       │
       ├─ 3. Run evaluation → EvaluationResult
       │
       ├─ 4. Score RMM level → RMMLevel
       │
       ├─ 5. Load audit-history.json (previous runs)
       │      └─ Compute trend arrows (↑/↓/→)
       │
       ├─ 6. Identify worst-performing samples
       │      └─ Root cause: retrieval failure vs. generation failure
       │
       ├─ 7. Generate HTML report (enhanced template)
       │      ├─ Radar chart (inline SVG)
       │      ├─ Trend arrows per metric
       │      ├─ Per-sample breakdown (collapsible)
       │      ├─ Worst queries highlighted
       │      ├─ Cost analysis (if token data available)
       │      └─ Actionable recommendations
       │
       ├─ 8. Generate JSON report (audit-report.json)
       │      └─ Machine-readable for CI gate
       │
       └─ 9. Append to audit-history.json
```

## Components

### 1. RagasEvaluator

**Location:** `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py`

```python
class RagasEvaluator:
    """Evaluator using the RAGAS framework.

    Requires: pip install rag-forge-evaluator[ragas]
    Wraps RAGAS v2 metrics: faithfulness, context_relevancy,
    answer_relevancy, and context_recall.
    """

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult: ...
    def supported_metrics(self) -> list[str]: ...
```

Dependencies: `ragas>=0.2` as optional dep. RAGAS uses LLM calls internally (OpenAI by default). The evaluator converts our `EvaluationSample` dataclass to RAGAS `Dataset` format, runs evaluation, and converts results back to our `EvaluationResult`.

Error handling: If RAGAS is not installed, importing the class raises `ImportError` with a clear message. The factory in `AuditOrchestrator` catches this and reports a helpful error.

### 2. DeepEvalEvaluator

**Location:** `packages/evaluator/src/rag_forge_evaluator/engines/deepeval_evaluator.py`

```python
class DeepEvalEvaluator:
    """Evaluator using the DeepEval framework.

    Requires: pip install rag-forge-evaluator[deepeval]
    Wraps DeepEval metrics: faithfulness, contextual_relevancy,
    answer_relevancy, and hallucination.
    """

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationResult: ...
    def supported_metrics(self) -> list[str]: ...
```

Dependencies: `deepeval>=1.0` as optional dep. Same pattern as RAGAS — convert samples, run evaluation, convert results.

### 3. Evaluator Engine Directory

**Location:** `packages/evaluator/src/rag_forge_evaluator/engines/__init__.py`

Factory function to create the right evaluator:

```python
def create_evaluator(engine: str, judge: JudgeProvider | None = None, thresholds: dict[str, float] | None = None) -> EvaluatorInterface:
    if engine == "llm-judge":
        return LLMJudgeEvaluator(judge=judge, thresholds=thresholds)
    elif engine == "ragas":
        from rag_forge_evaluator.engines.ragas_evaluator import RagasEvaluator
        return RagasEvaluator(thresholds=thresholds)
    elif engine == "deepeval":
        from rag_forge_evaluator.engines.deepeval_evaluator import DeepEvalEvaluator
        return DeepEvalEvaluator(thresholds=thresholds)
    else:
        raise ValueError(f"Unknown evaluator engine: {engine!r}")
```

### 4. Audit History

**Location:** `packages/evaluator/src/rag_forge_evaluator/history.py`

```python
@dataclass
class AuditHistoryEntry:
    """A single historical audit run."""

    timestamp: str                    # ISO-8601 UTC
    metrics: dict[str, float]         # metric_name → score
    rmm_level: int
    overall_score: float
    passed: bool


class AuditHistory:
    """Reads/writes audit-history.json for trend tracking."""

    def __init__(self, history_path: Path) -> None: ...

    def load(self) -> list[AuditHistoryEntry]:
        """Load previous audit entries. Returns empty list if file doesn't exist."""
        ...

    def append(self, entry: AuditHistoryEntry) -> None:
        """Append a new entry and write back to disk."""
        ...

    def get_previous(self) -> AuditHistoryEntry | None:
        """Get the most recent previous entry for trend comparison."""
        ...
```

The history file is `<output_dir>/audit-history.json`. Format:

```json
[
  {"timestamp": "2026-04-12T10:00:00Z", "metrics": {"faithfulness": 0.87, "context_relevance": 0.82}, "rmm_level": 3, "overall_score": 0.85, "passed": true},
  {"timestamp": "2026-04-10T15:30:00Z", "metrics": {"faithfulness": 0.82, "context_relevance": 0.78}, "rmm_level": 2, "overall_score": 0.80, "passed": false}
]
```

### 5. Per-Sample Results

**Location:** `packages/evaluator/src/rag_forge_evaluator/engine.py` (modify existing)

Add a new dataclass to capture per-sample detail:

```python
@dataclass
class SampleResult:
    """Evaluation results for a single sample."""

    query: str
    response: str
    metrics: dict[str, float]           # metric_name → score
    worst_metric: str                   # name of lowest-scoring metric
    root_cause: str                     # "retrieval" or "generation" or "both"
```

The `root_cause` is determined by:
- If `context_relevance < threshold` → "retrieval" (retrieved chunks weren't relevant)
- If `faithfulness < threshold` → "generation" (LLM hallucinated despite good context)
- If both → "both"
- If neither → "none"

`EvaluationResult` gains a `sample_results: list[SampleResult]` field (default empty, backward compatible).

### 6. Enhanced Report Generator

**Location:** `packages/evaluator/src/rag_forge_evaluator/report/generator.py` (modify existing)

Changes to `ReportGenerator`:

1. `generate_html()` signature gains `history: list[AuditHistoryEntry] | None = None` and `sample_results: list[SampleResult] | None = None`.

2. Template receives new variables:
   - `radar_svg` — pre-rendered SVG string for the radar chart
   - `trends` — dict of `{metric_name: "↑" | "↓" | "→"}` computed from history
   - `sample_results` — list of per-sample dicts for the breakdown section
   - `worst_samples` — top 3 worst-performing samples with root cause

3. New method `_generate_radar_svg(metrics: list[MetricResult]) -> str` — generates an inline SVG spider chart. Uses pure Python string construction (no chart libraries). The chart has one axis per metric, with the score plotted as a filled polygon.

4. New method `_compute_trends(current: dict[str, float], previous: AuditHistoryEntry | None) -> dict[str, str]` — compares current vs. previous scores. Returns `"↑"` if improved by ≥0.02, `"↓"` if declined by ≥0.02, `"→"` if stable.

### 7. JSON Report Output

**Location:** `packages/evaluator/src/rag_forge_evaluator/report/generator.py` (modify existing)

New method on `ReportGenerator`:

```python
def generate_json(
    self, result: EvaluationResult, rmm_level: RMMLevel,
    sample_results: list[SampleResult] | None = None,
) -> Path:
    """Write machine-readable audit-report.json alongside the HTML."""
    ...
```

JSON structure:

```json
{
  "timestamp": "2026-04-12T10:00:00Z",
  "overall_score": 0.87,
  "passed": true,
  "rmm_level": 3,
  "rmm_name": "Better Trust",
  "samples_evaluated": 10,
  "metrics": {
    "faithfulness": {"score": 0.90, "threshold": 0.85, "passed": true},
    "context_relevance": {"score": 0.82, "threshold": 0.80, "passed": true}
  },
  "worst_samples": [
    {"query": "...", "worst_metric": "faithfulness", "score": 0.45, "root_cause": "generation"}
  ]
}
```

### 8. Enhanced HTML Template

**Location:** `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2` (modify existing)

New sections added to the template:

1. **Radar chart** — `{{ radar_svg | safe }}` rendered as inline SVG below the summary cards
2. **Metrics table enhanced** — each row gains a trend arrow column: `{{ trends.get(m.name, "→") }}`
3. **Per-sample breakdown** — collapsible `<details>` section listing each sample with its per-metric scores, worst metric highlighted in red, and root cause badge
4. **Worst queries** — highlighted box at the top of per-sample section showing top 3 worst queries with root cause analysis
5. **Cost analysis** — section showing estimated monthly cost (only rendered if token data is available in samples)
6. **Visual improvements** — better gradient backgrounds, card shadows, metric bar charts alongside scores, RMM badge with level-appropriate colors

### 9. Updated AuditOrchestrator

**Location:** `packages/evaluator/src/rag_forge_evaluator/audit.py` (modify existing)

Changes:
1. `AuditConfig` gains `evaluator_engine: str = "llm-judge"` field
2. `run()` uses `create_evaluator(engine)` factory instead of hardcoding `LLMJudgeEvaluator`
3. After evaluation, loads `AuditHistory` and computes trends
4. Passes `history` and `sample_results` to `ReportGenerator.generate_html()`
5. Calls `ReportGenerator.generate_json()` to write machine-readable output
6. Appends current run to `AuditHistory`
7. `AuditReport` gains `json_report_path: Path` field

### 10. Updated CLI

**Location:** `packages/evaluator/src/rag_forge_evaluator/cli.py` (modify existing)

New argument: `--evaluator` with choices `llm-judge`, `ragas`, `deepeval` (default: `llm-judge`).

JSON stdout output gains `json_report_path` field.

**Location:** `packages/cli/src/commands/audit.ts` (modify existing)

New flag: `--evaluator <engine>` with default `"llm-judge"`.

Updated output display: shows evaluator engine used, trend arrows if available.

### 11. CI/CD Gate Workflow

**Location:** `.github/workflows/rag-audit.yml` (modify existing)

Replace the placeholder with active steps:

```yaml
name: RAG Audit Gate
on:
  pull_request:
    branches: [main]
    paths:
      - 'packages/core/src/**'
      - 'packages/evaluator/src/**'
      - 'eval/**'
      - 'rag-forge.config.*'

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      - uses: astral-sh/setup-uv@v4
      - run: uv python install 3.11
      - run: pnpm install --frozen-lockfile
      - run: uv sync --all-packages

      - name: Run RAG Audit
        run: |
          pnpm exec rag-forge audit \
            --golden-set eval/golden_set.json \
            --judge mock \
            --output ./reports

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

Note: The gate uses `--judge mock` by default so CI doesn't need API keys. For real evaluation, teams set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` as repository secrets and change `--judge` to `claude` or `openai`.

## Dependencies

### New Python dependencies (packages/evaluator/pyproject.toml)

```toml
[project.optional-dependencies]
ragas = ["ragas>=0.2"]
deepeval = ["deepeval>=1.0"]
```

No new required dependencies.

## Testing Strategy

### Unit Tests

1. `test_ragas_evaluator.py` — Test `RagasEvaluator` import behavior when `ragas` is not installed (graceful error). Test with mocked `ragas` if possible, or skip.

2. `test_deepeval_evaluator.py` — Same pattern as RAGAS tests.

3. `test_history.py` — Test `AuditHistory` load/append/get_previous. Test empty file, missing file, multiple entries.

4. `test_radar_chart.py` — Test `_generate_radar_svg()` produces valid SVG with correct metric labels. Test with 4 metrics, test with 0 metrics.

5. `test_json_report.py` — Test `generate_json()` writes valid JSON with correct structure. Test all fields present.

6. `test_trends.py` — Test `_compute_trends()` returns correct arrows. Test improving, declining, stable, no history.

7. `test_sample_results.py` — Test `SampleResult` root cause logic. Test retrieval failure, generation failure, both, neither.

8. `test_enhanced_report.py` — Test enhanced HTML contains radar chart, trend arrows, per-sample section, worst queries section.

9. `test_evaluator_factory.py` — Test `create_evaluator()` returns correct type for each engine string. Test unknown engine raises.

### Integration

10. `test_audit_enhanced_integration.py` — Full audit with history: run twice, verify second run has trend arrows.

## File Summary

### New files:
- `packages/evaluator/src/rag_forge_evaluator/engines/__init__.py`
- `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py`
- `packages/evaluator/src/rag_forge_evaluator/engines/deepeval_evaluator.py`
- `packages/evaluator/src/rag_forge_evaluator/history.py`
- `packages/evaluator/tests/test_history.py`
- `packages/evaluator/tests/test_ragas_evaluator.py`
- `packages/evaluator/tests/test_deepeval_evaluator.py`
- `packages/evaluator/tests/test_radar_chart.py`
- `packages/evaluator/tests/test_json_report.py`
- `packages/evaluator/tests/test_trends.py`
- `packages/evaluator/tests/test_sample_results.py`
- `packages/evaluator/tests/test_enhanced_report.py`
- `packages/evaluator/tests/test_evaluator_factory.py`
- `packages/evaluator/tests/test_audit_enhanced_integration.py`

### Modified files:
- `packages/evaluator/pyproject.toml`
- `packages/evaluator/src/rag_forge_evaluator/engine.py`
- `packages/evaluator/src/rag_forge_evaluator/audit.py`
- `packages/evaluator/src/rag_forge_evaluator/report/generator.py`
- `packages/evaluator/src/rag_forge_evaluator/report/templates/audit_report.html.j2`
- `packages/evaluator/src/rag_forge_evaluator/cli.py`
- `packages/cli/src/commands/audit.ts`
- `.github/workflows/rag-audit.yml`
