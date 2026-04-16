# v0.2.3 Evaluator Bug Fixes — Design Spec

**Date:** 2026-04-16
**Scope:** `packages/evaluator` only
**Bugs addressed:** C4-3 (RAGAS score extraction), C4-4 (sample_id propagation)
**Evidence source:** PearMedica Cycle 4 audit (2026-04-16), RAGAS 0.4.x migration docs

---

## Context

RAG-Forge v0.2.2 fixed the RAGAS adapter's `.generate()` method (C3-2) and the `__version__` drift (C3-5). The RAGAS engine now runs all evaluations to completion with real API calls. But two bugs remain:

1. **C4-3 (HIGH):** Every RAGAS evaluation completes but score extraction fails with `ValueError: could not extract ragas score for metric '...'`. Three consecutive cycles of RAGAS failure (Cycles 2, 3, 4), each at a different layer. This is the last layer.

2. **C4-4 (LOW):** The report writes `sample_id: "(unknown)"` for every sample because the JSONL input loader never extracts case identifiers from the telemetry file.

Both bugs are in `packages/evaluator`. No other packages are affected.

---

## Bug 1: C4-3 — RAGAS Score Extraction `ValueError`

### Root Cause

`_extract_ragas_score()` in `ragas_evaluator.py:42-70` tries three extraction strategies on the raw `ragas.evaluate()` return value:

1. `result.get(metric_name)` — assumes dict-like (RAGAS 0.2.x)
2. `result[metric_name]` — assumes `__getitem__` (generic)
3. `getattr(result, metric_name)` — assumes attribute access

All three fail on RAGAS 0.4.x because the return type changed. Per the [RAGAS 0.3 to 0.4 migration guide](https://github.com/vibrantlabsai/ragas/blob/main/docs/howtos/migrations/migrate_from_v03_to_v04.md):

- `ragas.evaluate()` returns an `EvaluationResult` object with a `.scores` attribute.
- `.scores` is a **list of dicts**, one per sample: `[{"faithfulness": MetricResult(...), "answer_relevancy": MetricResult(...)}, ...]`
- Each value is a `MetricResult` object. The float score lives at `.value`, the explanation at `.reason`.
- The result also exposes `.to_pandas()` which returns a DataFrame with metric names as columns and float values as cells.

None of the three current strategies reach `.scores`, and even if they did, they'd get `MetricResult` objects instead of floats.

### Fix

**File:** `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py`

#### 1. Rewrite `_extract_ragas_score()` to handle RAGAS 0.4.x

The function currently returns a single aggregate `float`. Rewrite it to handle the 0.4.x shape while preserving backward compatibility:

```python
def _extract_ragas_score(result: object, name: str) -> float:
    """Extract an aggregate metric score from a RAGAS result object.

    Tries extraction strategies in order of RAGAS version likelihood:
    1. .scores list (RAGAS 0.4.x) — per-sample MetricResult objects
    2. .to_pandas() (RAGAS 0.4.x fallback) — DataFrame with metric columns
    3. .get() (RAGAS 0.2.x) — dict-like access
    4. [] indexing (generic)
    5. getattr (generic)

    Raises ValueError if all strategies fail.
    """
    # Strategy 1: RAGAS 0.4.x .scores attribute
    if hasattr(result, "scores") and isinstance(result.scores, list):
        values = []
        for entry in result.scores:
            if isinstance(entry, dict) and name in entry:
                raw = entry[name]
                # MetricResult has .value; plain float works directly
                val = getattr(raw, "value", None)
                if val is not None:
                    values.append(float(val))
                else:
                    try:
                        values.append(float(raw))
                    except (TypeError, ValueError):
                        pass
        if values:
            return sum(values) / len(values)

    # Strategy 2: RAGAS 0.4.x .to_pandas() fallback
    if hasattr(result, "to_pandas"):
        try:
            df = result.to_pandas()
            if name in df.columns:
                col = df[name].dropna()
                if len(col) > 0:
                    return float(col.mean())
        except Exception:
            pass

    # Strategy 3-5: Legacy RAGAS 0.2.x / 0.3.x (existing logic, preserved)
    if hasattr(result, "get"):
        try:
            value = result.get(name, None)
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            pass
    try:
        return float(result[name])
    except (KeyError, TypeError, ValueError, IndexError):
        pass
    if hasattr(result, name):
        try:
            return float(getattr(result, name))
        except (TypeError, ValueError):
            pass

    raise ValueError(f"could not extract ragas score for metric {name!r}")
```

#### 2. Add per-sample RAGAS score extraction

The current architecture only extracts aggregate scores from RAGAS — one float per metric across all samples. But RAGAS 0.4.x's `.scores` list gives per-sample breakdowns, which is the same granularity the llm-judge already provides.

Add a new helper:

```python
def _extract_per_sample_scores(
    result: object,
    metric_names: list[str],
    samples: list[EvaluationSample],
) -> list[dict[str, float | None]]:
    """Extract per-sample scores from RAGAS 0.4.x result.

    Returns a list of dicts (one per sample), each mapping metric name
    to float score or None if extraction failed for that cell.
    """
```

This feeds into the existing `EvaluationResult.sample_results` list so the report can show per-case RAGAS scores alongside llm-judge scores.

#### 3. Update `RagasEvaluator.evaluate()` caller logic

Lines 176-202 currently loop over `_METRIC_NAMES` and call `_extract_ragas_score(result, metric_name)` for aggregate scores only. Update to:

1. First try per-sample extraction via `_extract_per_sample_scores()`.
2. If per-sample extraction succeeds, compute aggregates from the per-sample data and populate `sample_results`.
3. Fall back to aggregate-only extraction (current behaviour) if per-sample extraction fails.
4. Any metric where extraction fails at both levels gets the existing `SkipRecord` fan-out.

### Unit Test

**File:** `packages/evaluator/tests/test_ragas_score_extraction.py`

```python
def test_extract_ragas_04x_metric_result():
    """Mock the RAGAS 0.4.x EvaluationResult shape and verify extraction."""
    
    class MockMetricResult:
        def __init__(self, value, reason=""):
            self.value = value
            self.reason = reason
    
    class MockEvaluationResult:
        def __init__(self, scores):
            self.scores = scores
    
    result = MockEvaluationResult(scores=[
        {"faithfulness": MockMetricResult(0.85), "answer_relevancy": MockMetricResult(0.92)},
        {"faithfulness": MockMetricResult(0.78), "answer_relevancy": MockMetricResult(0.88)},
    ])
    
    assert _extract_ragas_score(result, "faithfulness") == pytest.approx(0.815)
    assert _extract_ragas_score(result, "answer_relevancy") == pytest.approx(0.90)
    
    with pytest.raises(ValueError):
        _extract_ragas_score(result, "nonexistent_metric")


def test_extract_ragas_02x_dict_fallback():
    """Verify legacy dict-like access still works."""
    result = {"faithfulness": 0.85, "answer_relevancy": 0.92}
    assert _extract_ragas_score(result, "faithfulness") == 0.85


def test_extract_per_sample_scores():
    """Verify per-sample extraction from RAGAS 0.4.x result."""
    # ... similar mock, assert list of dicts returned
```

---

## Bug 2: C4-4 — `sample_id: "(unknown)"`

### Root Cause

`InputLoader.load_jsonl()` at `input_loader.py:40-48` constructs `EvaluationSample` without setting `sample_id`:

```python
samples.append(
    EvaluationSample(
        query=data["query"],
        contexts=data["contexts"],
        response=data["response"],
        expected_answer=data.get("expected_answer"),
        chunk_ids=data.get("chunk_ids"),
        # sample_id is never set — defaults to None
    )
)
```

`EvaluationSample.sample_id` is `str | None = None` (engine.py:33). The report generator falls back to `"(unknown)"` in five places across `generator.py`.

### Fix

**File:** `packages/evaluator/src/rag_forge_evaluator/input_loader.py`

Update `load_jsonl()` to extract `sample_id` from the JSONL data:

```python
# Try common ID field names, fall back to sequential
sample_id = (
    data.get("case_id")
    or data.get("sample_id")
    or data.get("id")
    or f"sample-{line_num:03d}"
)

samples.append(
    EvaluationSample(
        query=data["query"],
        contexts=data["contexts"],
        response=data["response"],
        expected_answer=data.get("expected_answer"),
        chunk_ids=data.get("chunk_ids"),
        sample_id=sample_id,
    )
)
```

**Priority order for field names:**
1. `case_id` — used by PearMedica's golden set and most common in RAG evaluation setups
2. `sample_id` — matches the internal field name
3. `id` — generic fallback
4. `sample-{line_num:03d}` — deterministic sequential ID when no identifier exists

The sequential fallback is stable across runs of the same file (same line order = same IDs). It's not stable if lines are reordered, but that's an acceptable trade-off for files that genuinely lack identifiers.

### No downstream changes needed

The report generator already reads `sample_id` and falls back to `"(unknown)"`. Once the loader populates it, every downstream consumer benefits automatically:
- `generator.py:152` (worst-case identification)
- `generator.py:216` (JSON report case_id)
- `generator.py:273, 284` (sample results)
- `generator.py:795` (skip records)
- `ragas_evaluator.py:246` (`_fan_out_skip_records` — already has its own fallback to `sample.query[:40]`)

### Unit Test

**File:** `packages/evaluator/tests/test_input_loader.py`

```python
def test_load_jsonl_extracts_case_id():
    """JSONL with case_id field populates sample_id."""
    jsonl = '{"case_id": "acs-001", "query": "q", "contexts": ["c"], "response": "r"}\n'
    # write to tmp file, load, assert sample.sample_id == "acs-001"


def test_load_jsonl_extracts_sample_id_field():
    """JSONL with sample_id field (no case_id) populates sample_id."""
    jsonl = '{"sample_id": "s-001", "query": "q", "contexts": ["c"], "response": "r"}\n'
    # assert sample.sample_id == "s-001"


def test_load_jsonl_sequential_fallback():
    """JSONL with no ID fields gets sequential sample-NNN IDs."""
    jsonl = '{"query": "q", "contexts": ["c"], "response": "r"}\n'
    # assert sample.sample_id == "sample-001"
```

---

## Out of Scope

| Item | Reason |
|------|--------|
| C3-4 (Context Relevance rubric drift) | Not a bug. Evaluation path changed in v0.2.0 from per-chunk to holistic. Already documented in v0.2.2 CHANGELOG. |
| BM25 keyword search returning zero | PearMedica's own PostgreSQL `plainto_tsquery` implementation. Not RAG-Forge code. |
| Retrieval quality (recall@5 = 0.38) | PearMedica pipeline tuning. |
| htn-001 generation variance | LLM stochastic output. PearMedica generation-side. |
| Hallucination < 0.95 threshold | PearMedica retrieval quality. |
| Similarity:0 on parent-expanded chunks | PearMedica pipeline instrumentation. |

---

## Release Plan

1. Both fixes land in `packages/evaluator` only.
2. Lockstep version bump to 0.2.3 across all 6 packages (per existing convention).
3. Validate with PearMedica Cycle 5: re-run `--evaluator ragas` and confirm scores are extracted. Re-run `--evaluator llm-judge` and confirm sample_id appears in the report.
4. RAGAS fix can be validated independently with a unit test before any API spend.

---

## Files Modified

| File | Change |
|------|--------|
| `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py` | Rewrite `_extract_ragas_score()`, add `_extract_per_sample_scores()`, update `evaluate()` caller |
| `packages/evaluator/src/rag_forge_evaluator/input_loader.py` | Extract `sample_id` from JSONL in `load_jsonl()` |
| `packages/evaluator/tests/test_ragas_score_extraction.py` | New — unit tests for RAGAS 0.4.x score extraction |
| `packages/evaluator/tests/test_input_loader.py` | New or extended — unit tests for sample_id extraction |
| `pyproject.toml` (all 3 Python packages) | Version bump 0.2.2 → 0.2.3 |
| `packages/cli/package.json`, `packages/mcp/package.json` | Version bump 0.2.2 → 0.2.3 |
