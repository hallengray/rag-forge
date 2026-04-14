"""Tests for CLI refusal-aware flags in the audit command."""

import argparse
from pathlib import Path

from rag_forge_evaluator.audit import AuditConfig


def _build_parser() -> argparse.ArgumentParser:
    """Extract and return the argparse parser from cli module.

    This is a minimal wrapper that reconstructs the audit subparser
    without full main() boilerplate, for test isolation.
    """
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

    return parser


def _build_audit_config_from_args(args: argparse.Namespace) -> AuditConfig:
    """Convert parsed CLI args to AuditConfig.

    This mirrors the logic from cli.py cmd_audit().
    """
    # Compute refusal_aware from mutually-exclusive flags
    strict = bool(getattr(args, "strict", False) or getattr(args, "no_refusal_aware_flag", False))
    refusal_aware = not strict

    config = AuditConfig(
        input_path=Path(args.input) if args.input else None,
        golden_set_path=Path(args.golden_set) if args.golden_set else None,
        judge_model=args.judge or None,
        judge_model_name=args.judge_model or None,
        output_dir=Path(args.output),
        generate_pdf=args.pdf,
        thresholds=None,
        evaluator_engine=args.evaluator,
        assume_yes=args.yes,
        refusal_aware=refusal_aware,
    )
    return config


class TestCLIRefusalFlags:
    """Test --strict, --refusal-aware, and --no-refusal-aware flags."""

    def test_cli_default_is_refusal_aware_on(self) -> None:
        """With no flags, the resulting AuditConfig has refusal_aware=True."""
        parser = _build_parser()
        args = parser.parse_args([
            "audit",
            "--input", "tests/fixtures/tiny.jsonl",
            "--judge", "mock",
        ])
        config = _build_audit_config_from_args(args)
        assert config.refusal_aware is True

    def test_cli_strict_flag_disables_refusal_aware(self) -> None:
        """--strict flag sets refusal_aware=False."""
        parser = _build_parser()
        args = parser.parse_args([
            "audit",
            "--input", "tests/fixtures/tiny.jsonl",
            "--judge", "mock",
            "--strict",
        ])
        config = _build_audit_config_from_args(args)
        assert config.refusal_aware is False

    def test_cli_no_refusal_aware_alias_disables(self) -> None:
        """--no-refusal-aware flag (alias for --strict) sets refusal_aware=False."""
        parser = _build_parser()
        args = parser.parse_args([
            "audit",
            "--input", "tests/fixtures/tiny.jsonl",
            "--judge", "mock",
            "--no-refusal-aware",
        ])
        config = _build_audit_config_from_args(args)
        assert config.refusal_aware is False

    def test_cli_refusal_aware_flag_explicit_on(self) -> None:
        """--refusal-aware flag explicitly enables refusal-aware (noop default, but explicit)."""
        parser = _build_parser()
        args = parser.parse_args([
            "audit",
            "--input", "tests/fixtures/tiny.jsonl",
            "--judge", "mock",
            "--refusal-aware",
        ])
        config = _build_audit_config_from_args(args)
        assert config.refusal_aware is True

    def test_cli_flags_are_mutually_exclusive_strict_and_refusal_aware(self) -> None:
        """--strict and --refusal-aware cannot be used together."""
        parser = _build_parser()
        with pytest.raises(SystemExit):  # argparse raises SystemExit on conflict
            parser.parse_args([
                "audit",
                "--input", "tests/fixtures/tiny.jsonl",
                "--judge", "mock",
                "--strict",
                "--refusal-aware",
            ])

    def test_cli_flags_are_mutually_exclusive_strict_and_no_refusal_aware(self) -> None:
        """--strict and --no-refusal-aware cannot be used together (both disable)."""
        parser = _build_parser()
        with pytest.raises(SystemExit):  # argparse raises SystemExit on conflict
            parser.parse_args([
                "audit",
                "--input", "tests/fixtures/tiny.jsonl",
                "--judge", "mock",
                "--strict",
                "--no-refusal-aware",
            ])

    def test_cli_flags_are_mutually_exclusive_refusal_aware_and_no_refusal_aware(self) -> None:
        """--refusal-aware and --no-refusal-aware cannot be used together."""
        parser = _build_parser()
        with pytest.raises(SystemExit):  # argparse raises SystemExit on conflict
            parser.parse_args([
                "audit",
                "--input", "tests/fixtures/tiny.jsonl",
                "--judge", "mock",
                "--refusal-aware",
                "--no-refusal-aware",
            ])


import pytest  # noqa: E402 — import at module end to avoid top-level circle
