"""RMM assessment: score a pipeline against the RAG Maturity Model.

Inspects configuration and optional audit data to determine the current
RMM level (0-5) without running a full evaluation.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AssessmentCheck:
    """A single check within an RMM level."""

    description: str
    passed: bool
    source: str  # "config", "audit", or "unknown"


@dataclass
class AssessmentResult:
    """Result of an RMM assessment."""

    rmm_level: int
    rmm_name: str
    criteria: list[dict[str, Any]]
    badge: str


_LEVEL_NAMES = {
    0: "Naive RAG",
    1: "Better Recall",
    2: "Better Precision",
    3: "Better Trust",
    4: "Better Workflow",
    5: "Enterprise",
}


class RMMAssessor:
    """Assesses a pipeline's RMM level from config and optional audit data."""

    def load_audit_metrics(self, report_path: str) -> dict[str, float]:
        """Load metric scores from an audit JSON report."""
        path = Path(report_path)
        with path.open() as f:
            data = json.load(f)
        metrics: dict[str, float] = {}
        for m in data.get("metrics", []):
            try:
                metrics[str(m["name"])] = float(m["score"])
            except (KeyError, ValueError, TypeError):
                continue
        return metrics

    def assess(
        self,
        config: dict[str, Any],
        audit_metrics: dict[str, float] | None = None,
    ) -> AssessmentResult:
        """Determine RMM level from pipeline configuration and audit data."""
        metrics = audit_metrics or {}
        all_criteria: list[dict[str, Any]] = []
        current_level = 0

        def _to_dict(checks: list[AssessmentCheck]) -> list[dict[str, Any]]:
            return [
                {"description": c.description, "passed": c.passed, "source": c.source}
                for c in checks
            ]

        # RMM-0: Naive RAG — always passes
        checks_0 = [AssessmentCheck("Pipeline exists", True, "config")]
        all_criteria.append(
            {"level": 0, "name": "Naive RAG", "passed": True, "checks": _to_dict(checks_0)}
        )

        # RMM-1: Better Recall
        hybrid = config.get("retrieval_strategy") == "hybrid"
        sparse = bool(config.get("sparse_index_configured", False))
        recall_ok = metrics.get("recall_at_k", 0.0) >= 0.70
        checks_1 = [
            AssessmentCheck("Hybrid search configured", hybrid, "config"),
            AssessmentCheck("Sparse index configured", sparse, "config"),
            AssessmentCheck(
                "Recall@5 >= 70%",
                recall_ok,
                "audit" if "recall_at_k" in metrics else "unknown",
            ),
        ]
        level1_passed = hybrid and sparse and recall_ok
        if level1_passed:
            current_level = 1
        all_criteria.append(
            {
                "level": 1,
                "name": "Better Recall",
                "passed": level1_passed,
                "checks": _to_dict(checks_1),
            }
        )

        # RMM-2: Better Precision
        reranker = bool(config.get("reranker_configured", False))
        ndcg_ok = metrics.get("ndcg_improvement", 0.0) >= 0.10
        checks_2 = [
            AssessmentCheck("Reranker active", reranker, "config"),
            AssessmentCheck(
                "nDCG@10 improvement >= 10%",
                ndcg_ok,
                "audit" if "ndcg_improvement" in metrics else "unknown",
            ),
        ]
        level2_passed = level1_passed and reranker and ndcg_ok
        if level2_passed:
            current_level = 2
        all_criteria.append(
            {
                "level": 2,
                "name": "Better Precision",
                "passed": level2_passed,
                "checks": _to_dict(checks_2),
            }
        )

        # RMM-3: Better Trust
        input_guard = bool(config.get("input_guard_configured", False))
        output_guard = bool(config.get("output_guard_configured", False))
        faith_ok = metrics.get("faithfulness", 0.0) >= 0.85
        ctx_ok = metrics.get("context_relevance", 0.0) >= 0.80
        checks_3 = [
            AssessmentCheck("InputGuard active", input_guard, "config"),
            AssessmentCheck("OutputGuard active", output_guard, "config"),
            AssessmentCheck(
                "Faithfulness >= 85%",
                faith_ok,
                "audit" if "faithfulness" in metrics else "unknown",
            ),
            AssessmentCheck(
                "Context relevance >= 80%",
                ctx_ok,
                "audit" if "context_relevance" in metrics else "unknown",
            ),
        ]
        level3_passed = (
            current_level >= 2 and input_guard and output_guard and faith_ok and ctx_ok
        )
        if level3_passed:
            current_level = 3
        all_criteria.append(
            {
                "level": 3,
                "name": "Better Trust",
                "passed": level3_passed,
                "checks": _to_dict(checks_3),
            }
        )

        # RMM-4: Better Workflow
        caching = bool(config.get("caching_configured", False))
        latency_ok = metrics.get("latency_p95", 99999.0) <= 4000
        cost_tracked = bool(config.get("cost_tracking_configured", False))
        checks_4 = [
            AssessmentCheck("Semantic caching active", caching, "config"),
            AssessmentCheck(
                "P95 latency < 4s",
                latency_ok,
                "audit" if "latency_p95" in metrics else "unknown",
            ),
            AssessmentCheck("Cost per query tracked", cost_tracked, "config"),
        ]
        level4_passed = current_level >= 3 and caching and latency_ok and cost_tracked
        if level4_passed:
            current_level = 4
        all_criteria.append(
            {
                "level": 4,
                "name": "Better Workflow",
                "passed": level4_passed,
                "checks": _to_dict(checks_4),
            }
        )

        # RMM-5: Enterprise
        drift = bool(config.get("drift_detection_configured", False))
        ci_gates = bool(config.get("ci_cd_gates_configured", False))
        adversarial_ok = bool(config.get("adversarial_tests_passing", False))
        checks_5 = [
            AssessmentCheck("Drift detection live", drift, "config"),
            AssessmentCheck("CI/CD evaluation gates configured", ci_gates, "config"),
            AssessmentCheck("Adversarial tests green", adversarial_ok, "config"),
        ]
        level5_passed = level4_passed and drift and ci_gates and adversarial_ok
        if level5_passed:
            current_level = 5
        all_criteria.append(
            {
                "level": 5,
                "name": "Enterprise",
                "passed": level5_passed,
                "checks": _to_dict(checks_5),
            }
        )

        name = _LEVEL_NAMES.get(current_level, "Unknown")
        badge = f"RMM-{current_level} {name}"

        return AssessmentResult(
            rmm_level=current_level,
            rmm_name=name,
            criteria=all_criteria,
            badge=badge,
        )
