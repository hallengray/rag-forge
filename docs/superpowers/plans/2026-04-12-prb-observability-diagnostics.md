# PR B: Observability & Diagnostics Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `rag-forge report`, `rag-forge cache stats`, and `rag-forge inspect` — the pipeline diagnostics commands.

**Architecture:** `report` aggregates existing data (audit reports, pipeline state) into a health dashboard HTML. `cache stats` reads persisted cache metrics. `inspect` is a TS wrapper for an existing Python command. All follow the TS→Python bridge pattern.

**Tech Stack:** Python 3.11+, Jinja2 (HTML reports), pytest, TypeScript (Commander.js)

**Branch:** `feat/prb-observability-diagnostics`

---

### Task 1: Health Report Generator

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/report/health.py`
- Create: `packages/evaluator/tests/test_health_report.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/evaluator/tests/test_health_report.py
"""Tests for pipeline health report generator."""

import json
from pathlib import Path

from rag_forge_evaluator.report.health import HealthReportGenerator, PipelineHealth


class TestPipelineHealth:
    def test_from_empty_state(self) -> None:
        health = PipelineHealth.collect(reports_dir=None, collection_name="test")
        assert health.chunk_count == 0
        assert health.latest_audit is None

    def test_from_audit_report(self, tmp_path: Path) -> None:
        report_path = tmp_path / "audit-report.json"
        report_data = {
            "overall_score": 0.82,
            "rmm_level": 3,
            "rmm_name": "Better Trust",
            "metrics": [
                {"name": "faithfulness", "score": 0.88, "threshold": 0.85, "passed": True},
            ],
        }
        report_path.write_text(json.dumps(report_data))

        health = PipelineHealth.collect(reports_dir=str(tmp_path), collection_name="test")
        assert health.latest_audit is not None
        assert health.latest_audit["overall_score"] == 0.82


class TestHealthReportGenerator:
    def test_generates_html_file(self, tmp_path: Path) -> None:
        health = PipelineHealth(chunk_count=100, latest_audit=None, drift_baseline_exists=False)
        gen = HealthReportGenerator(output_dir=str(tmp_path))
        path = gen.generate(health)
        assert path.exists()
        assert path.suffix == ".html"

    def test_html_contains_chunk_count(self, tmp_path: Path) -> None:
        health = PipelineHealth(chunk_count=42, latest_audit=None, drift_baseline_exists=False)
        gen = HealthReportGenerator(output_dir=str(tmp_path))
        path = gen.generate(health)
        content = path.read_text()
        assert "42" in content

    def test_html_contains_audit_data_when_present(self, tmp_path: Path) -> None:
        health = PipelineHealth(
            chunk_count=100,
            latest_audit={"overall_score": 0.85, "rmm_level": 3, "rmm_name": "Better Trust", "metrics": []},
            drift_baseline_exists=True,
        )
        gen = HealthReportGenerator(output_dir=str(tmp_path))
        path = gen.generate(health)
        content = path.read_text()
        assert "Better Trust" in content
```

- [ ] **Step 2: Implement PipelineHealth and HealthReportGenerator**

```python
# packages/evaluator/src/rag_forge_evaluator/report/health.py
"""Pipeline health report generator.

Aggregates existing data (audit reports, pipeline state) into a
standalone HTML dashboard. No LLM calls — pure aggregation.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class PipelineHealth:
    """Collected pipeline health state."""

    chunk_count: int = 0
    latest_audit: dict[str, Any] | None = None
    drift_baseline_exists: bool = False

    @classmethod
    def collect(
        cls,
        reports_dir: str | None = None,
        collection_name: str = "rag-forge",
    ) -> "PipelineHealth":
        """Collect pipeline state from available sources."""
        latest_audit = None
        if reports_dir:
            report_path = Path(reports_dir) / "audit-report.json"
            if report_path.exists():
                with report_path.open() as f:
                    latest_audit = json.load(f)

        drift_exists = Path("drift-baseline.json").exists()

        # Chunk count: try Qdrant, fall back to 0
        chunk_count = 0
        try:
            from rag_forge_core.storage.qdrant import QdrantStore

            store = QdrantStore()
            chunk_count = store.count(collection_name)
        except Exception:
            pass

        return cls(
            chunk_count=chunk_count,
            latest_audit=latest_audit,
            drift_baseline_exists=drift_exists,
        )


class HealthReportGenerator:
    """Generates a standalone HTML pipeline health dashboard."""

    def __init__(self, output_dir: str = "./reports") -> None:
        self.output_dir = Path(output_dir)

    def generate(self, health: PipelineHealth) -> Path:
        """Generate the health report HTML."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

        audit_section = ""
        if health.latest_audit:
            audit = health.latest_audit
            rmm_name = audit.get("rmm_name", "Unknown")
            rmm_level = audit.get("rmm_level", 0)
            overall = audit.get("overall_score", 0.0)
            metrics_html = ""
            for m in audit.get("metrics", []):
                status = "PASS" if m.get("passed") else "FAIL"
                metrics_html += f"<tr><td>{m['name']}</td><td>{m['score']:.2f}</td><td>{status}</td></tr>"

            audit_section = f"""
            <div class="section">
                <h2>Latest Audit</h2>
                <div class="badge">RMM-{rmm_level}: {rmm_name}</div>
                <p>Overall Score: {overall:.2f}</p>
                <table><tr><th>Metric</th><th>Score</th><th>Status</th></tr>{metrics_html}</table>
            </div>"""

        drift_status = "Baseline configured" if health.drift_baseline_exists else "No baseline"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>RAG-Forge Pipeline Health Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }}
        h1 {{ color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 10px; }}
        .section {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        .badge {{ display: inline-block; background: #e94560; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; }}
        .stat {{ font-size: 2em; font-weight: bold; color: #1a1a2e; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #1a1a2e; color: white; }}
    </style>
</head>
<body>
    <h1>RAG-Forge Pipeline Health</h1>
    <p>Generated: {timestamp}</p>

    <div class="section">
        <h2>Pipeline State</h2>
        <p>Indexed Chunks: <span class="stat">{health.chunk_count}</span></p>
        <p>Drift Detection: {drift_status}</p>
    </div>

    {audit_section}
</body>
</html>"""

        output_path = self.output_dir / "health-report.html"
        output_path.write_text(html, encoding="utf-8")
        return output_path
```

- [ ] **Step 3: Run tests, ruff, commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/report/health.py packages/evaluator/tests/test_health_report.py
git commit -m "feat(evaluator): add pipeline health report generator"
```

---

### Task 2: Cache Stats Python Command

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py` (add `cache-stats` subcommand)

- [ ] **Step 1: Add `cmd_cache_stats` to core CLI**

```python
def cmd_cache_stats(args: argparse.Namespace) -> None:
    """Report semantic cache statistics."""
    stats_path = Path("./cache/stats.json")

    if stats_path.exists():
        try:
            with stats_path.open() as f:
                stats = json.load(f)
            output = {
                "success": True,
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "total": stats.get("total", 0),
                "hit_rate": stats.get("hits", 0) / max(stats.get("total", 1), 1),
                "source": "persisted",
            }
        except Exception as e:
            output = {"success": False, "error": f"Failed to read cache stats: {e}"}
    else:
        output = {
            "success": True,
            "hits": 0,
            "misses": 0,
            "total": 0,
            "hit_rate": 0.0,
            "source": "none",
            "message": "No cache data available — cache stats are tracked during MCP server sessions",
        }

    json.dump(output, sys.stdout)
```

Add subparser and dispatch in `main()`:
```python
    cache_parser = subparsers.add_parser("cache-stats", help="Show semantic cache stats")
```

```python
    elif args.command == "cache-stats":
        cmd_cache_stats(args)
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py
git commit -m "feat(cli): add cache-stats Python entry point"
```

---

### Task 3: Report + Cache Stats + Inspect Python CLI Entry Points

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/cli.py` (add `report` subcommand)

- [ ] **Step 1: Add `cmd_report` to evaluator CLI**

```python
def cmd_report(args: argparse.Namespace) -> None:
    """Generate pipeline health report."""
    from rag_forge_evaluator.report.health import HealthReportGenerator, PipelineHealth

    try:
        health = PipelineHealth.collect(
            reports_dir=args.output,
            collection_name=args.collection or "rag-forge",
        )
        gen = HealthReportGenerator(output_dir=args.output)
        path = gen.generate(health)

        output = {
            "success": True,
            "report_path": str(path),
            "chunk_count": health.chunk_count,
            "has_audit": health.latest_audit is not None,
            "drift_baseline": health.drift_baseline_exists,
        }
    except Exception as e:
        output = {"success": False, "error": str(e)}

    json.dump(output, sys.stdout)
```

Add subparser and dispatch.

- [ ] **Step 2: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/cli.py
git commit -m "feat(cli): add report Python entry point"
```

---

### Task 4: TypeScript CLI Commands (report, cache, inspect)

**Files:**
- Create: `packages/cli/src/commands/report.ts`
- Create: `packages/cli/src/commands/cache.ts`
- Create: `packages/cli/src/commands/inspect.ts`
- Modify: `packages/cli/src/index.ts`

- [ ] **Step 1: Create all three TS command files**

Each follows the established pattern:
- `report.ts`: calls `rag_forge_evaluator.cli report`, displays report path
- `cache.ts`: calls `rag_forge_core.cli cache-stats`, displays hit rate and counts
- `inspect.ts`: calls `rag_forge_core.cli inspect`, displays chunk text and metadata

- [ ] **Step 2: Register in index.ts**

- [ ] **Step 3: TypeScript check + lint**

- [ ] **Step 4: Commit**

```bash
git add packages/cli/src/commands/report.ts packages/cli/src/commands/cache.ts packages/cli/src/commands/inspect.ts packages/cli/src/index.ts
git commit -m "feat(cli): add report, cache stats, inspect TypeScript commands"
```

---

### Task 5: Push and Open PR

- [ ] **Step 1: Full build quality check**
- [ ] **Step 2: Push and create PR**

```bash
git push -u origin feat/prb-observability-diagnostics
gh pr create --title "feat: add report, cache stats, inspect diagnostic commands" --body "..."
```
