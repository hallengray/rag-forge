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
