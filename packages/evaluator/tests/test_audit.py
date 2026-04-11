"""Integration tests for the audit orchestrator."""

import json
from pathlib import Path

from rag_forge_evaluator.audit import AuditConfig, AuditOrchestrator, AuditReport
from rag_forge_evaluator.maturity import RMMLevel


class TestAuditOrchestrator:
    def _make_jsonl(self, tmp_path: Path) -> Path:
        jsonl = tmp_path / "telemetry.jsonl"
        lines = [
            {"query": "What is Python?", "contexts": ["Python is a language."], "response": "Python is a programming language."},
            {"query": "What is Rust?", "contexts": ["Rust is fast."], "response": "Rust is a systems programming language."},
            {"query": "What is Go?", "contexts": ["Go is concurrent."], "response": "Go is a language by Google."},
        ]
        jsonl.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
        return jsonl

    def test_full_audit_from_jsonl(self, tmp_path: Path) -> None:
        jsonl = self._make_jsonl(tmp_path)
        config = AuditConfig(input_path=jsonl, judge_model="mock", output_dir=tmp_path / "reports")
        report = AuditOrchestrator(config).run()
        assert isinstance(report, AuditReport)
        assert report.samples_evaluated == 3
        assert len(report.evaluation.metrics) == 4
        assert report.report_path.exists()

    def test_audit_generates_html(self, tmp_path: Path) -> None:
        jsonl = self._make_jsonl(tmp_path)
        config = AuditConfig(input_path=jsonl, judge_model="mock", output_dir=tmp_path / "reports")
        report = AuditOrchestrator(config).run()
        html = report.report_path.read_text(encoding="utf-8")
        assert "RAG-Forge Audit Report" in html
        assert "faithfulness" in html

    def test_audit_with_golden_set(self, tmp_path: Path) -> None:
        gs = tmp_path / "golden.json"
        gs.write_text(json.dumps([{"query": "What is RAG?", "expected_answer_keywords": ["retrieval", "augmented"]}]), encoding="utf-8")
        config = AuditConfig(golden_set_path=gs, judge_model="mock", output_dir=tmp_path / "reports")
        report = AuditOrchestrator(config).run()
        assert report.samples_evaluated == 1

    def test_audit_rmm_level(self, tmp_path: Path) -> None:
        jsonl = self._make_jsonl(tmp_path)
        config = AuditConfig(input_path=jsonl, judge_model="mock", output_dir=tmp_path / "reports")
        report = AuditOrchestrator(config).run()
        assert isinstance(report.rmm_level, RMMLevel)
