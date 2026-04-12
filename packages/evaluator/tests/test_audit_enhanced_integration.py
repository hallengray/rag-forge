"""Integration test: full audit with history and enhanced reports."""

import json
import tempfile
from pathlib import Path

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator


def _create_test_jsonl(path: Path) -> None:
    """Create a small test JSONL file."""
    samples = [
        {"query": "What is Python?", "contexts": ["Python is a programming language."], "response": "Python is a programming language."},
        {"query": "What is Rust?", "contexts": ["Rust is a systems language."], "response": "Rust provides memory safety."},
        {"query": "What is JavaScript?", "contexts": ["JavaScript runs in browsers."], "response": "JavaScript powers web apps."},
    ]
    path.write_text("\n".join(json.dumps(s) for s in samples), encoding="utf-8")


class TestAuditEnhancedIntegration:
    def test_full_audit_produces_html_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)

            config = AuditConfig(input_path=jsonl, output_dir=tmp / "reports")
            report = AuditOrchestrator(config).run()

            assert report.report_path.exists()
            assert report.json_report_path.exists()
            assert report.report_path.suffix == ".html"
            assert report.json_report_path.suffix == ".json"

    def test_json_report_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)

            config = AuditConfig(input_path=jsonl, output_dir=tmp / "reports")
            report = AuditOrchestrator(config).run()

            data = json.loads(report.json_report_path.read_text(encoding="utf-8"))
            assert "metrics" in data
            assert "faithfulness" in data["metrics"]
            assert data["samples_evaluated"] == 3

    def test_history_appended_after_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)
            output_dir = tmp / "reports"

            config = AuditConfig(input_path=jsonl, output_dir=output_dir)
            AuditOrchestrator(config).run()

            history_path = output_dir / "audit-history.json"
            assert history_path.exists()
            history = json.loads(history_path.read_text(encoding="utf-8"))
            assert len(history) == 1

    def test_second_run_has_trends(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)
            output_dir = tmp / "reports"

            config = AuditConfig(input_path=jsonl, output_dir=output_dir)
            AuditOrchestrator(config).run()
            report2 = AuditOrchestrator(config).run()

            history_path = output_dir / "audit-history.json"
            history = json.loads(history_path.read_text(encoding="utf-8"))
            assert len(history) == 2

            html = report2.report_path.read_text(encoding="utf-8")
            assert "<svg" in html

    def test_html_contains_per_sample_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "input.jsonl"
            _create_test_jsonl(jsonl)

            config = AuditConfig(input_path=jsonl, output_dir=tmp / "reports")
            report = AuditOrchestrator(config).run()

            html = report.report_path.read_text(encoding="utf-8")
            assert "What is Python?" in html
