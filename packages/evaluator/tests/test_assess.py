"""Tests for RMM assessment."""

import json
from pathlib import Path

from rag_forge_evaluator.assess import RMMAssessor


class TestRMMAssessor:
    def test_empty_config_returns_rmm0(self) -> None:
        assessor = RMMAssessor()
        result = assessor.assess(config={})
        assert result.rmm_level == 0
        assert result.rmm_name == "Naive RAG"

    def test_hybrid_config_returns_rmm1(self) -> None:
        assessor = RMMAssessor()
        result = assessor.assess(config={
            "retrieval_strategy": "hybrid",
            "sparse_index_configured": True,
        }, audit_metrics={"recall_at_k": 0.75})
        assert result.rmm_level >= 1

    def test_reranker_config_returns_rmm2(self) -> None:
        assessor = RMMAssessor()
        result = assessor.assess(config={
            "retrieval_strategy": "hybrid",
            "sparse_index_configured": True,
            "reranker_configured": True,
        }, audit_metrics={"recall_at_k": 0.75, "ndcg_improvement": 0.12})
        assert result.rmm_level >= 2

    def test_guardrails_returns_rmm3(self) -> None:
        assessor = RMMAssessor()
        result = assessor.assess(config={
            "retrieval_strategy": "hybrid",
            "sparse_index_configured": True,
            "reranker_configured": True,
            "input_guard_configured": True,
            "output_guard_configured": True,
        }, audit_metrics={
            "recall_at_k": 0.75,
            "ndcg_improvement": 0.12,
            "faithfulness": 0.90,
            "context_relevance": 0.85,
        })
        assert result.rmm_level >= 3

    def test_result_includes_checks(self) -> None:
        assessor = RMMAssessor()
        result = assessor.assess(config={})
        assert len(result.criteria) > 0
        for criteria in result.criteria:
            assert "level" in criteria
            assert "checks" in criteria

    def test_result_includes_badge(self) -> None:
        assessor = RMMAssessor()
        result = assessor.assess(config={})
        assert "RMM-0" in result.badge

    def test_from_audit_report(self, tmp_path: Path) -> None:
        report_path = tmp_path / "audit-report.json"
        report_data = {
            "overall_score": 0.82,
            "metrics": [
                {"name": "faithfulness", "score": 0.88, "threshold": 0.85, "passed": True},
                {"name": "context_relevance", "score": 0.81, "threshold": 0.80, "passed": True},
                {"name": "recall_at_k", "score": 0.72, "threshold": 0.70, "passed": True},
            ],
        }
        report_path.write_text(json.dumps(report_data))

        assessor = RMMAssessor()
        metrics = assessor.load_audit_metrics(str(report_path))
        assert metrics["faithfulness"] == 0.88
        assert metrics["recall_at_k"] == 0.72
