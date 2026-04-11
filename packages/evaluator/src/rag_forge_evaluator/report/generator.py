"""HTML audit report generator using Jinja2 templates."""

from datetime import UTC, datetime
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

    def generate_html(self, result: EvaluationResult, rmm_level: RMMLevel) -> Path:
        """Generate a standalone HTML report."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)
        template = env.get_template("audit_report.html.j2")

        rmm_name = next(
            (c.name for c in RMM_CRITERIA if c.level == rmm_level), "Unknown"
        )

        html = template.render(
            timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC"),
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
