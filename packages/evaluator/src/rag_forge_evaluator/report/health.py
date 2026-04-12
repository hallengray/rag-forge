"""Pipeline health report generator.

Aggregates existing data (audit reports, pipeline state) into a
standalone HTML dashboard. No LLM calls — pure aggregation.
"""

import json
from dataclasses import dataclass
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

        chunk_count = 0
        try:
            from rag_forge_core.storage.qdrant import QdrantStore  # type: ignore[import-untyped]

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
        """Generate an HTML health report from collected pipeline state."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

        audit_section = self._build_audit_section(health)
        drift_status = "Baseline configured" if health.drift_baseline_exists else "No baseline"

        html = self._render_html(timestamp, health.chunk_count, drift_status, audit_section)

        output_path = self.output_dir / "health-report.html"
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def _build_audit_section(self, health: PipelineHealth) -> str:
        """Build the audit section HTML if audit data is available."""
        if not health.latest_audit:
            return ""

        audit = health.latest_audit
        rmm_name = audit.get("rmm_name", "Unknown")
        rmm_level = audit.get("rmm_level", 0)
        overall = audit.get("overall_score", 0.0)

        metrics_html = ""
        for m in audit.get("metrics", []):
            status = "PASS" if m.get("passed") else "FAIL"
            metrics_html += (
                f"<tr><td>{m['name']}</td>"
                f"<td>{m['score']:.2f}</td>"
                f"<td>{status}</td></tr>"
            )

        return f"""
            <div class="section">
                <h2>Latest Audit</h2>
                <div class="badge">RMM-{rmm_level}: {rmm_name}</div>
                <p>Overall Score: {overall:.2f}</p>
                <table>
                    <tr><th>Metric</th><th>Score</th><th>Status</th></tr>
                    {metrics_html}
                </table>
            </div>"""

    def _render_html(
        self,
        timestamp: str,
        chunk_count: int,
        drift_status: str,
        audit_section: str,
    ) -> str:
        """Render the full HTML health report."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>RAG-Forge Pipeline Health Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            color: #333;
        }}
        h1 {{
            color: #1a1a2e;
            border-bottom: 2px solid #e94560;
            padding-bottom: 10px;
        }}
        .section {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .badge {{
            display: inline-block;
            background: #e94560;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
        }}
        .stat {{
            font-size: 2em;
            font-weight: bold;
            color: #1a1a2e;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #1a1a2e;
            color: white;
        }}
    </style>
</head>
<body>
    <h1>RAG-Forge Pipeline Health</h1>
    <p>Generated: {timestamp}</p>
    <div class="section">
        <h2>Pipeline State</h2>
        <p>Indexed Chunks: <span class="stat">{chunk_count}</span></p>
        <p>Drift Detection: {drift_status}</p>
    </div>
    {audit_section}
</body>
</html>"""
