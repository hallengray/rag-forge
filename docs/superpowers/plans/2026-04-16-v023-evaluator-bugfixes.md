# v0.2.3 Evaluator Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix RAGAS 0.4.x score extraction (C4-3) and sample_id propagation (C4-4) in rag-forge-evaluator.

**Architecture:** Two isolated fixes in `packages/evaluator`. The RAGAS fix rewrites `_extract_ragas_score()` to handle the 0.4.x `EvaluationResult.scores` shape (list of dicts containing `MetricResult` objects with `.value`). The sample_id fix adds ID extraction to the JSONL input loader. Both are TDD — failing test first, then implementation.

**Tech Stack:** Python 3.11+, pytest, dataclasses. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-16-v023-evaluator-bugfixes-design.md`

---

### Task 1: RAGAS 0.4.x score extraction — failing tests

**Files:**
- Modify: `packages/evaluator/tests/test_ragas_extractor.py`

- [ ] **Step 1: Add test for RAGAS 0.4.x `.scores` list with `MetricResult` objects**

Append to the end of `packages/evaluator/tests/test_ragas_extractor.py`:

```python
def test_extract_from_ragas_04x_scores_list() -> None:
    """ragas 0.4.x: result.scores is a list of dicts mapping metric name
    to MetricResult objects with a .value attribute. The extractor should
    average per-sample scores into one aggregate float."""

    @dataclass
    class _MetricResult:
        value: float
        reason: str = ""

    class _Result:
        def __init__(self, scores: list[dict[str, _MetricResult]]) -> None:
            self.scores = scores

    result = _Result(scores=[
        {"faithfulness": _MetricResult(0.90), "answer_relevancy": _MetricResult(0.80)},
        {"faithfulness": _MetricResult(0.70), "answer_relevancy": _MetricResult(0.60)},
    ])
    assert _extract_ragas_score(result, "faithfulness") == pytest.approx(0.80)
    assert _extract_ragas_score(result, "answer_relevancy") == pytest.approx(0.70)


def test_extract_from_ragas_04x_scores_with_plain_floats() -> None:
    """ragas 0.4.x edge case: some metrics may return plain floats
    instead of MetricResult in the scores list."""

    class _Result:
        def __init__(self, scores: list[dict[str, float]]) -> None:
            self.scores = scores

    result = _Result(scores=[
        {"faithfulness": 0.85},
        {"faithfulness": 0.75},
    ])
    assert _extract_ragas_score(result, "faithfulness") == pytest.approx(0.80)


def test_extract_from_ragas_04x_to_pandas_fallback() -> None:
    """ragas 0.4.x fallback: if .scores doesn't contain the metric,
    fall back to .to_pandas() DataFrame extraction.

    We mock to_pandas() with a lightweight duck-typed object to avoid
    a hard pandas dependency in the evaluator test suite.
    """

    class _FakeColumn:
        """Mimics a pandas Series with .dropna(), len(), and .mean()."""
        def __init__(self, values: list[float]) -> None:
            self._values = values
        def dropna(self) -> "_FakeColumn":
            return _FakeColumn([v for v in self._values if v is not None])
        def __len__(self) -> int:
            return len(self._values)
        def mean(self) -> float:
            return sum(self._values) / len(self._values)

    class _FakeDataFrame:
        """Mimics a pandas DataFrame with column access."""
        def __init__(self, data: dict[str, list[float]]) -> None:
            self._data = data
            self.columns = list(data.keys())
        def __getitem__(self, key: str) -> _FakeColumn:
            return _FakeColumn(self._data[key])

    class _Result:
        def __init__(self) -> None:
            self.scores: list[dict] = []  # empty — forces fallback

        def to_pandas(self) -> _FakeDataFrame:
            return _FakeDataFrame({"faithfulness": [0.90, 0.70]})

    result = _Result()
    assert _extract_ragas_score(result, "faithfulness") == pytest.approx(0.80)


def test_extract_from_ragas_04x_missing_metric_in_scores() -> None:
    """ragas 0.4.x: metric not present in any scores entry AND no
    to_pandas fallback should raise ValueError."""

    class _Result:
        def __init__(self) -> None:
            self.scores = [{"other_metric": 0.5}]

    with pytest.raises(ValueError):
        _extract_ragas_score(_Result(), "faithfulness")
```

The `dataclass` import already exists at line 3 and `pytest` at line 5. No new imports needed — the `to_pandas` test uses inline duck-typed mocks to avoid a pandas dependency.

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd packages/evaluator && uv run pytest tests/test_ragas_extractor.py -v -k "04x"
```

Expected: All four new tests FAIL — `_extract_ragas_score` doesn't handle `.scores` or `.to_pandas()`.

- [ ] **Step 3: Commit failing tests**

```bash
git add packages/evaluator/tests/test_ragas_extractor.py
git commit -m "test(evaluator): add failing tests for RAGAS 0.4.x score extraction (C4-3)"
```

---

### Task 2: RAGAS 0.4.x score extraction — implementation

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py:42-70`

- [ ] **Step 1: Rewrite `_extract_ragas_score()` to handle RAGAS 0.4.x**

Replace lines 42-70 in `packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py` with:

```python
def _extract_ragas_score(result: object, name: str) -> float:
    """Extract an aggregate metric score from a ragas result object.

    Tries extraction strategies in order of RAGAS version likelihood:

    1. ``.scores`` list (RAGAS 0.4.x) — per-sample ``MetricResult``
       objects whose float score lives at ``.value``.
    2. ``.to_pandas()`` (RAGAS 0.4.x fallback) — DataFrame with metric
       names as columns and float values as cells.
    3. ``.get()`` (RAGAS 0.2.x) — dict-like access.
    4. ``[]`` indexing (generic).
    5. ``getattr`` (generic).

    Raises ``ValueError`` if all strategies fail — the caller decides
    whether to record a ``SkipRecord`` or re-raise.  No silent 0.0
    fallback (that was the bug surfaced by Cycle 2).
    """
    # --- Strategy 1: RAGAS 0.4.x .scores attribute ---
    # result.scores is a list[dict[str, MetricResult | float]], one dict
    # per sample. MetricResult wraps the float at .value.
    scores_attr = getattr(result, "scores", None)
    if isinstance(scores_attr, list) and scores_attr:
        values: list[float] = []
        for entry in scores_attr:
            if isinstance(entry, dict) and name in entry:
                raw = entry[name]
                val = getattr(raw, "value", None)
                if val is not None:
                    try:
                        values.append(float(val))
                    except (TypeError, ValueError):
                        pass
                else:
                    try:
                        values.append(float(raw))
                    except (TypeError, ValueError):
                        pass
        if values:
            return sum(values) / len(values)

    # --- Strategy 2: RAGAS 0.4.x .to_pandas() fallback ---
    to_pandas = getattr(result, "to_pandas", None)
    if callable(to_pandas):
        try:
            df = to_pandas()
            if name in df.columns:
                col = df[name].dropna()
                if len(col) > 0:
                    return float(col.mean())
        except Exception:  # noqa: BLE001 — defensive fallback
            pass

    # --- Strategy 3: RAGAS 0.2.x dict-like .get() ---
    if hasattr(result, "get"):
        try:
            value = result.get(name, None)  # type: ignore[union-attr]
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            pass

    # --- Strategy 4: generic __getitem__ ---
    try:
        return float(result[name])  # type: ignore[index]
    except (KeyError, TypeError, ValueError, IndexError):
        pass

    # --- Strategy 5: generic attribute access ---
    if hasattr(result, name):
        try:
            return float(getattr(result, name))
        except (TypeError, ValueError):
            pass

    raise ValueError(f"could not extract ragas score for metric {name!r}")
```

- [ ] **Step 2: Run all extractor tests**

Run:
```bash
cd packages/evaluator && uv run pytest tests/test_ragas_extractor.py -v
```

Expected: All tests pass — the four new 0.4.x tests AND the seven existing legacy tests.

- [ ] **Step 3: Run the full evaluator test suite to check for regressions**

Run:
```bash
cd packages/evaluator && uv run pytest tests/ -v --timeout=60
```

Expected: All existing tests pass. No regressions.

- [ ] **Step 4: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/engines/ragas_evaluator.py
git commit -m "fix(evaluator): rewrite RAGAS score extraction for 0.4.x MetricResult shape (C4-3)"
```

---

### Task 3: sample_id JSONL extraction — failing tests

**Files:**
- Modify: `packages/evaluator/tests/test_input_loader.py`

- [ ] **Step 1: Add tests for sample_id extraction**

Append to the `TestLoadJsonl` class in `packages/evaluator/tests/test_input_loader.py`:

```python
    def test_extracts_case_id_as_sample_id(self, tmp_path: Path) -> None:
        """JSONL with case_id field should populate sample_id."""
        jsonl = tmp_path / "with_case_id.jsonl"
        jsonl.write_text(
            json.dumps({"case_id": "acs-001-typical-stemi", "query": "q", "contexts": ["c"], "response": "r"}),
            encoding="utf-8",
        )
        samples = InputLoader.load_jsonl(jsonl)
        assert samples[0].sample_id == "acs-001-typical-stemi"

    def test_extracts_sample_id_field(self, tmp_path: Path) -> None:
        """JSONL with sample_id field (no case_id) should populate sample_id."""
        jsonl = tmp_path / "with_sample_id.jsonl"
        jsonl.write_text(
            json.dumps({"sample_id": "s-001", "query": "q", "contexts": ["c"], "response": "r"}),
            encoding="utf-8",
        )
        samples = InputLoader.load_jsonl(jsonl)
        assert samples[0].sample_id == "s-001"

    def test_extracts_id_field_as_fallback(self, tmp_path: Path) -> None:
        """JSONL with only 'id' field should use it as sample_id."""
        jsonl = tmp_path / "with_id.jsonl"
        jsonl.write_text(
            json.dumps({"id": "entry-42", "query": "q", "contexts": ["c"], "response": "r"}),
            encoding="utf-8",
        )
        samples = InputLoader.load_jsonl(jsonl)
        assert samples[0].sample_id == "entry-42"

    def test_case_id_takes_priority_over_sample_id(self, tmp_path: Path) -> None:
        """When both case_id and sample_id exist, case_id wins."""
        jsonl = tmp_path / "both_ids.jsonl"
        jsonl.write_text(
            json.dumps({"case_id": "from-case", "sample_id": "from-sample", "query": "q", "contexts": ["c"], "response": "r"}),
            encoding="utf-8",
        )
        samples = InputLoader.load_jsonl(jsonl)
        assert samples[0].sample_id == "from-case"

    def test_sequential_fallback_when_no_id_field(self, tmp_path: Path) -> None:
        """JSONL with no ID fields should get sequential sample-NNN IDs."""
        jsonl = tmp_path / "no_ids.jsonl"
        lines = [
            json.dumps({"query": "q1", "contexts": ["c"], "response": "r1"}),
            json.dumps({"query": "q2", "contexts": ["c"], "response": "r2"}),
        ]
        jsonl.write_text("\n".join(lines), encoding="utf-8")
        samples = InputLoader.load_jsonl(jsonl)
        assert samples[0].sample_id == "sample-001"
        assert samples[1].sample_id == "sample-002"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd packages/evaluator && uv run pytest tests/test_input_loader.py -v -k "sample_id or case_id or sequential"
```

Expected: All five new tests FAIL — `sample_id` is `None` because `load_jsonl` doesn't extract it.

- [ ] **Step 3: Commit failing tests**

```bash
git add packages/evaluator/tests/test_input_loader.py
git commit -m "test(evaluator): add failing tests for sample_id JSONL extraction (C4-4)"
```

---

### Task 4: sample_id JSONL extraction — implementation

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/input_loader.py:40-48`

- [ ] **Step 1: Add sample_id extraction to `load_jsonl()`**

Replace lines 40-48 in `packages/evaluator/src/rag_forge_evaluator/input_loader.py` with:

```python
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

- [ ] **Step 2: Run the input loader tests**

Run:
```bash
cd packages/evaluator && uv run pytest tests/test_input_loader.py -v
```

Expected: All tests pass — the five new sample_id tests AND the existing tests.

- [ ] **Step 3: Run the full evaluator test suite**

Run:
```bash
cd packages/evaluator && uv run pytest tests/ -v --timeout=60
```

Expected: All tests pass. No regressions.

- [ ] **Step 4: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/input_loader.py
git commit -m "fix(evaluator): extract sample_id from JSONL input — case_id > sample_id > id > sequential (C4-4)"
```

---

### Task 5: Version bump 0.2.2 to 0.2.3

**Files:**
- Modify: `packages/evaluator/pyproject.toml:3`
- Modify: `packages/core/pyproject.toml:3`
- Modify: `packages/observability/pyproject.toml:3`
- Modify: `packages/cli/package.json:3`
- Modify: `packages/mcp/package.json:3`
- Modify: `packages/shared/package.json:3`
- Modify: `packages/evaluator/src/rag_forge_evaluator/__init__.py:3`
- Modify: `packages/core/src/rag_forge_core/__init__.py:3`
- Modify: `packages/observability/src/rag_forge_observability/__init__.py:5`

- [ ] **Step 1: Bump all 9 version locations from 0.2.2 to 0.2.3**

In each of these files, replace `0.2.2` with `0.2.3`:

| File | Line | Change |
|------|------|--------|
| `packages/evaluator/pyproject.toml` | 3 | `version = "0.2.2"` → `version = "0.2.3"` |
| `packages/core/pyproject.toml` | 3 | `version = "0.2.2"` → `version = "0.2.3"` |
| `packages/observability/pyproject.toml` | 3 | `version = "0.2.2"` → `version = "0.2.3"` |
| `packages/cli/package.json` | 3 | `"version": "0.2.2"` → `"version": "0.2.3"` |
| `packages/mcp/package.json` | 3 | `"version": "0.2.2"` → `"version": "0.2.3"` |
| `packages/shared/package.json` | 3 | `"version": "0.2.2"` → `"version": "0.2.3"` |
| `packages/evaluator/src/rag_forge_evaluator/__init__.py` | 3 | `__version__ = "0.2.2"` → `__version__ = "0.2.3"` |
| `packages/core/src/rag_forge_core/__init__.py` | 3 | `__version__ = "0.2.2"` ��� `__version__ = "0.2.3"` |
| `packages/observability/src/rag_forge_observability/__init__.py` | 5 | `__version__ = "0.2.2"` → `__version__ = "0.2.3"` |

- [ ] **Step 2: Run the version drift guard**

Run:
```bash
cd packages/evaluator && uv run pytest tests/test_version_drift.py -v
```

Expected: PASS — the drift guard confirms `__version__` matches `pyproject.toml`.

- [ ] **Step 3: Commit**

```bash
git add packages/evaluator/pyproject.toml packages/core/pyproject.toml packages/observability/pyproject.toml packages/cli/package.json packages/mcp/package.json packages/shared/package.json packages/evaluator/src/rag_forge_evaluator/__init__.py packages/core/src/rag_forge_core/__init__.py packages/observability/src/rag_forge_observability/__init__.py
git commit -m "chore(release): bump all packages to v0.2.3"
```

---

### Task 6: Full build verification

**Files:** None — verification only.

- [ ] **Step 1: Run Python type checking**

Run:
```bash
uv run mypy packages/evaluator/src --ignore-missing-imports
```

Expected: No new errors.

- [ ] **Step 2: Run Python linting**

Run:
```bash
uv run ruff check packages/evaluator/src packages/evaluator/tests
```

Expected: No errors or warnings.

- [ ] **Step 3: Run the full test suite**

Run:
```bash
cd packages/evaluator && uv run pytest tests/ -v --timeout=60
```

Expected: All tests pass.

- [ ] **Step 4: Run TypeScript build (lockstep version sanity)**

Run:
```bash
pnpm run build
```

Expected: Clean build, no errors.

- [ ] **Step 5: Run TypeScript linting and type checking**

Run:
```bash
pnpm run lint && pnpm run typecheck
```

Expected: No errors or warnings.
