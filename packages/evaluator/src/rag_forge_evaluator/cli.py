"""Python CLI entry point for the rag-forge audit command.

Called via: uv run python -m rag_forge_evaluator.cli audit --input telemetry.jsonl
Outputs JSON to stdout for the TypeScript CLI to parse.
"""

import argparse
import contextlib
import json
import sys
from pathlib import Path

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator, PartialAuditError
from rag_forge_evaluator.judge.claude_judge import OverloadBudgetExhaustedError
from rag_forge_evaluator.progress import StderrProgressReporter
from rag_forge_observability.tracing import TracingManager

# Exit codes. Documented in --help and release notes. CI scripts can
# distinguish a partial audit (3) from a usage error (2, argparse default)
# or a hard failure (1) or a clean run (0).
EXIT_OK = 0
EXIT_HARD_FAILURE = 1
EXIT_PARTIAL = 3


def _stderr_retry_notice(attempt: int, elapsed: float, budget: float) -> None:
    """Print a one-line retry notice to stderr when ClaudeJudge hits a 529.

    Stays off the ProgressReporter protocol on purpose: the judge has multiple
    callers (tests, programmatic use, MCP server) and shouldn't unilaterally
    decide that stderr is the right output channel. The CLI is the one place
    that knows stderr is where progress already lives, so the wiring lives here.
    """
    sys.stderr.write(
        f"  [judge: 529 overload, retry {attempt}, "
        f"elapsed {elapsed:.0f}s / {budget:.0f}s budget]\n"
    )
    sys.stderr.flush()

# Ensure line-buffered output when invoked as a subprocess on Windows.
# Without this, a long-running audit looks completely frozen until exit
# because Python block-buffers stdout when it is not connected to a TTY.
with contextlib.suppress(AttributeError, OSError):
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
with contextlib.suppress(AttributeError, OSError):
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[union-attr]


def cmd_audit(args: argparse.Namespace) -> None:
    """Run the audit command."""
    config_data = json.loads(args.config_json) if args.config_json else {}

    tracing = TracingManager()
    tracing.enable()
    tracer = tracing.get_tracer() if tracing.is_enabled() else None

    # Compute refusal_aware from mutually-exclusive flags
    strict = bool(getattr(args, "strict", False) or getattr(args, "no_refusal_aware_flag", False))
    refusal_aware = not strict

    config = AuditConfig(
        input_path=Path(args.input) if args.input else None,
        golden_set_path=Path(args.golden_set) if args.golden_set else None,
        judge_model=args.judge or config_data.get("judge_model", "mock"),
        judge_model_name=args.judge_model or config_data.get("judge_model_name"),
        output_dir=Path(args.output),
        generate_pdf=args.pdf,
        thresholds=config_data.get("thresholds"),
        evaluator_engine=args.evaluator,
        tracer=tracer,
        progress=StderrProgressReporter(),
        assume_yes=args.yes,
        on_judge_retry=_stderr_retry_notice,
        refusal_aware=refusal_aware,
    )

    try:
        report = AuditOrchestrator(config).run()
    except PartialAuditError as partial:
        # Partial-run artifact is already on disk. Print a diagnostic and
        # return a distinct exit code so CI scripts can branch on it.
        sys.stderr.write(
            f"\nAudit aborted at sample {partial.completed_samples}/{partial.total_samples} "
            f"({partial.aborted_reason}).\n"
            f"Partial report: {partial.partial_report_path}\n"
            f"Original error: {type(partial.original).__name__}: {partial.original}\n"
        )
        if isinstance(partial.original, OverloadBudgetExhaustedError):
            sys.stderr.write(
                "\nAnthropic was in a sustained 529 overload event. Options:\n"
                "  (a) wait 10-15 minutes and re-run\n"
                "  (b) switch judges with --judge openai\n"
                "  (c) increase the budget: "
                "RAG_FORGE_JUDGE_OVERLOAD_BUDGET_SECONDS=600\n"
            )
        json.dump(
            {
                "success": False,
                "partial": True,
                "partial_report_path": str(partial.partial_report_path),
                "completed_samples": partial.completed_samples,
                "total_samples": partial.total_samples,
                "aborted_reason": partial.aborted_reason,
                "error": f"{type(partial.original).__name__}: {partial.original}",
            },
            sys.stdout,
        )
        tracing.shutdown()
        sys.exit(EXIT_PARTIAL)

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


def cmd_assess(args: argparse.Namespace) -> None:
    """Run RMM assessment."""
    from rag_forge_evaluator.assess import RMMAssessor

    try:
        config_data = json.loads(args.config_json) if args.config_json else {}
        assessor = RMMAssessor()
        audit_metrics: dict[str, float] | None = None
        if args.audit_report:
            audit_metrics = assessor.load_audit_metrics(args.audit_report)
        result = assessor.assess(config=config_data, audit_metrics=audit_metrics)
        output = {
            "success": True,
            "rmm_level": result.rmm_level,
            "rmm_name": result.rmm_name,
            "badge": result.badge,
            "criteria": result.criteria,
        }
    except Exception as e:
        json.dump({"success": False, "error": str(e)}, sys.stdout)
        sys.exit(1)
    json.dump(output, sys.stdout)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="rag-forge-evaluator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Run evaluation audit")
    audit_parser.add_argument("--input", help="Path to telemetry JSONL file")
    audit_parser.add_argument("--golden-set", help="Path to golden set JSON file")
    audit_parser.add_argument("--judge", help="Judge provider alias: mock | claude | openai")
    audit_parser.add_argument(
        "--judge-model",
        help=(
            "Specific judge model id passed through to the provider "
            "(e.g. 'claude-opus-4-6', 'gpt-4-turbo'). "
            "Falls back to RAG_FORGE_JUDGE_MODEL env var, then the provider default."
        ),
    )
    audit_parser.add_argument("--output", default="./reports", help="Output directory")
    audit_parser.add_argument("--config-json", help="JSON config from TS CLI")
    audit_parser.add_argument(
        "--evaluator", default="llm-judge",
        choices=["llm-judge", "ragas", "deepeval"],
        help="Evaluator engine: llm-judge | ragas | deepeval",
    )
    audit_parser.add_argument("--pdf", action="store_true", help="Generate PDF report")
    audit_parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip the pre-run confirmation prompt. Required for non-interactive runs.",
    )

    # Refusal-aware flags (mutually exclusive group)
    refusal_group = audit_parser.add_mutually_exclusive_group()
    refusal_group.add_argument(
        "--strict",
        action="store_true",
        help="Revert to v0.1.x scoring semantics. Safety refusals are penalized as non-answers.",
    )
    refusal_group.add_argument(
        "--refusal-aware",
        dest="refusal_aware_flag",
        action="store_true",
        help="Force refusal-aware scoring on (default behavior).",
    )
    refusal_group.add_argument(
        "--no-refusal-aware",
        dest="no_refusal_aware_flag",
        action="store_true",
        help="Alias for --strict.",
    )

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

    report_parser = subparsers.add_parser("report", help="Generate pipeline health report")
    report_parser.add_argument("--output", default="./reports", help="Output directory")
    report_parser.add_argument("--collection", help="Collection name", default="rag-forge")

    golden_validate_parser = subparsers.add_parser("golden-validate", help="Validate golden set")
    golden_validate_parser.add_argument("--golden-set", required=True, help="Path to golden set JSON")

    assess_parser = subparsers.add_parser("assess", help="Run RMM assessment")
    assess_parser.add_argument("--config-json", help="Pipeline config as JSON")
    assess_parser.add_argument("--audit-report", help="Path to latest audit JSON report")

    args = parser.parse_args()
    if args.command == "audit":
        cmd_audit(args)
    elif args.command == "cost":
        cmd_cost(args)
    elif args.command == "golden-add":
        cmd_golden_add(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "golden-validate":
        cmd_golden_validate(args)
    elif args.command == "assess":
        cmd_assess(args)


if __name__ == "__main__":
    main()
