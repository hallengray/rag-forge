"""Python CLI entry point for the rag-forge audit command.

Called via: uv run python -m rag_forge_evaluator.cli audit --input telemetry.jsonl
Outputs JSON to stdout for the TypeScript CLI to parse.
"""

import argparse
import json
import sys
from pathlib import Path

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator
from rag_forge_observability.tracing import TracingManager


def cmd_audit(args: argparse.Namespace) -> None:
    """Run the audit command."""
    config_data = json.loads(args.config_json) if args.config_json else {}

    tracing = TracingManager()
    tracing.enable()
    tracer = tracing.get_tracer() if tracing.is_enabled() else None

    config = AuditConfig(
        input_path=Path(args.input) if args.input else None,
        golden_set_path=Path(args.golden_set) if args.golden_set else None,
        judge_model=args.judge or config_data.get("judge_model", "mock"),
        output_dir=Path(args.output),
        generate_pdf=args.pdf,
        thresholds=config_data.get("thresholds"),
        evaluator_engine=args.evaluator,
        tracer=tracer,
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
        "json_report_path": str(report.json_report_path),
        "evaluator_engine": config.evaluator_engine,
        "pdf_report_path": str(report.pdf_report_path) if report.pdf_report_path else None,
    }
    json.dump(output, sys.stdout)
    tracing.shutdown()


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
    audit_parser.add_argument(
        "--evaluator", default="llm-judge",
        choices=["llm-judge", "ragas", "deepeval"],
        help="Evaluator engine: llm-judge | ragas | deepeval",
    )
    audit_parser.add_argument("--pdf", action="store_true", help="Generate PDF report")

    args = parser.parse_args()
    if args.command == "audit":
        cmd_audit(args)


if __name__ == "__main__":
    main()
