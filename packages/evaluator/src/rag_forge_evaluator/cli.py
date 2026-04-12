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


def cmd_cost(args: argparse.Namespace) -> None:
    """Run the cost estimation command."""
    from rag_forge_evaluator.cost import CostEstimator

    try:
        with Path(args.telemetry).open() as f:
            data = json.load(f)
    except Exception as e:
        json.dump({"success": False, "error": f"Failed to load telemetry: {e}"}, sys.stdout)
        sys.exit(1)

    usage = data.get("usage", [])
    raw_qpd = args.queries_per_day if args.queries_per_day is not None else data.get("queries_per_day", 100)
    queries_per_day = int(raw_qpd)
    if queries_per_day < 0:
        json.dump({"success": False, "error": "queries_per_day must be >= 0"}, sys.stdout)
        sys.exit(1)

    estimator = CostEstimator()
    report = estimator.estimate(usage, queries_per_day)

    output = {
        "success": True,
        "daily_cost": report.daily_cost,
        "monthly_cost": report.monthly_cost,
        "queries_per_day": report.queries_per_day,
        "breakdown": report.breakdown,
    }
    json.dump(output, sys.stdout)


def cmd_golden_add(args: argparse.Namespace) -> None:
    """Add entries to a golden set."""
    from rag_forge_evaluator.golden_set import GoldenSet

    try:
        gs = GoldenSet()
        golden_path = Path(args.golden_set)

        # Load existing if present
        if golden_path.exists():
            gs.load(golden_path)

        if args.from_traffic:
            added = gs.add_from_traffic(args.from_traffic, sample_size=args.sample_size)
            gs.save(golden_path)
            json.dump({
                "success": True,
                "added": added,
                "total": len(gs.entries),
                "golden_set_path": str(golden_path),
                "source": "traffic",
            }, sys.stdout)
        elif args.query and args.keywords:
            keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
            if not keywords:
                json.dump({"success": False, "error": "--keywords must include at least one non-empty keyword"}, sys.stdout)
                sys.exit(1)
            gs.add_entry(
                query=args.query,
                expected_answer_keywords=keywords,
                difficulty=args.difficulty or "medium",
                topic=args.topic or "general",
            )
            gs.save(golden_path)
            json.dump({
                "success": True,
                "added": 1,
                "total": len(gs.entries),
                "golden_set_path": str(golden_path),
                "source": "manual",
            }, sys.stdout)
        else:
            json.dump({
                "success": False,
                "error": "Provide --from-traffic <file> or --query <q> --keywords <k1,k2>",
            }, sys.stdout)
            sys.exit(1)
    except Exception as e:
        json.dump({"success": False, "error": str(e)}, sys.stdout)
        sys.exit(1)


def cmd_golden_validate(args: argparse.Namespace) -> None:
    """Validate a golden set."""
    from rag_forge_evaluator.golden_set import GoldenSet

    try:
        gs = GoldenSet()
        golden_path = Path(args.golden_set)
        gs.load(golden_path)
        errors = gs.validate()
        json.dump({
            "success": True,
            "valid": len(errors) == 0,
            "total_entries": len(gs.entries),
            "errors": errors,
        }, sys.stdout)
    except Exception as e:
        json.dump({"success": False, "error": str(e)}, sys.stdout)
        sys.exit(1)


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

    cost_parser = subparsers.add_parser("cost", help="Estimate pipeline costs")
    cost_parser.add_argument("--telemetry", required=True, help="Path to telemetry JSON")
    cost_parser.add_argument("--queries-per-day", type=int, help="Projected daily queries")

    golden_add_parser = subparsers.add_parser("golden-add", help="Add golden set entries")
    golden_add_parser.add_argument("--golden-set", required=True, help="Path to golden set JSON")
    golden_add_parser.add_argument("--from-traffic", help="Path to telemetry JSONL to sample from")
    golden_add_parser.add_argument("--sample-size", type=int, default=10, help="Number of entries to sample (>= 1)")
    golden_add_parser.add_argument("--query", help="Question to add")
    golden_add_parser.add_argument("--keywords", help="Comma-separated expected keywords")
    golden_add_parser.add_argument("--difficulty", help="Difficulty: easy | medium | hard")
    golden_add_parser.add_argument("--topic", help="Topic category")

    golden_validate_parser = subparsers.add_parser("golden-validate", help="Validate golden set")
    golden_validate_parser.add_argument("--golden-set", required=True, help="Path to golden set JSON")

    args = parser.parse_args()
    if args.command == "audit":
        cmd_audit(args)
    elif args.command == "cost":
        cmd_cost(args)
    elif args.command == "golden-add":
        cmd_golden_add(args)
    elif args.command == "golden-validate":
        cmd_golden_validate(args)


if __name__ == "__main__":
    main()
