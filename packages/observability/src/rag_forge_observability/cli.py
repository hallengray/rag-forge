"""Python CLI entry point for observability commands.

Called via: uv run python -m rag_forge_observability.cli drift-report --current ... --baseline ...
Outputs JSON to stdout for the TypeScript CLI to parse.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rag_forge_observability.drift import DriftBaseline, DriftDetector


def cmd_drift_save_baseline(
    embeddings_path: str,
    baseline_path: str,
) -> dict[str, Any]:
    """Save embeddings as a drift baseline."""
    try:
        path = Path(embeddings_path)
        with path.open() as f:
            data = json.load(f)
        embeddings = data["embeddings"]

        detector = DriftDetector()
        detector.save_baseline(embeddings, baseline_path)
        return {
            "success": True,
            "baseline_path": baseline_path,
            "vectors_saved": len(embeddings),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def cmd_drift_report(
    current_path: str,
    baseline_path: str,
    threshold: float = 0.15,
) -> dict[str, Any]:
    """Generate a drift report comparing current embeddings to baseline."""
    try:
        baseline = DriftBaseline.load(baseline_path)
    except Exception as e:
        return {"success": False, "error": str(e)}

    try:
        with Path(current_path).open() as f:
            data = json.load(f)
        current = data["embeddings"]
    except Exception as e:
        return {"success": False, "error": f"Failed to load current embeddings: {e}"}

    detector = DriftDetector(threshold=threshold)
    report = detector.analyze(current_embeddings=current, baseline=baseline)

    return {
        "success": True,
        "is_drifting": report.is_drifting,
        "distance": report.baseline_distance,
        "threshold": report.threshold,
        "details": report.details,
    }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="rag-forge-observability")
    subparsers = parser.add_subparsers(dest="command", required=True)

    save_parser = subparsers.add_parser("drift-save-baseline", help="Save drift baseline")
    save_parser.add_argument("--embeddings", required=True, help="Path to embeddings JSON")
    save_parser.add_argument("--output", required=True, help="Path to save baseline")

    report_parser = subparsers.add_parser("drift-report", help="Generate drift report")
    report_parser.add_argument("--current", required=True, help="Path to current embeddings JSON")
    report_parser.add_argument("--baseline", required=True, help="Path to baseline JSON")
    report_parser.add_argument("--threshold", type=float, default=0.15, help="Drift threshold")

    args = parser.parse_args()
    if args.command == "drift-save-baseline":
        result = cmd_drift_save_baseline(args.embeddings, args.output)
    elif args.command == "drift-report":
        result = cmd_drift_report(args.current, args.baseline, args.threshold)
    else:
        result = {"success": False, "error": f"Unknown command: {args.command}"}

    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
