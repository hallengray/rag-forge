"""RAG Maturity Model (RMM) scoring: RMM-0 through RMM-5."""

from dataclasses import dataclass
from enum import IntEnum


class RMMLevel(IntEnum):
    """RAG Maturity Model levels."""

    NAIVE = 0       # Basic vector search, no evaluation
    RECALL = 1      # Hybrid search, Recall@5 > 70%
    PRECISION = 2   # Reranker active, nDCG@10 +10%
    TRUST = 3       # Guardrails, faithfulness > 85%, citations
    WORKFLOW = 4    # Caching, P95 < 4s, TTFT < 2s, cost tracking
    ENTERPRISE = 5  # RBAC, drift detection, CI/CD gates, adversarial tests


@dataclass
class RMMCriteria:
    """Exit criteria for a given RMM level."""

    level: RMMLevel
    name: str
    description: str
    requirements: list[str]


RMM_CRITERIA: list[RMMCriteria] = [
    RMMCriteria(
        level=RMMLevel.NAIVE,
        name="Naive RAG",
        description="Basic vector search works; queries return relevant results",
        requirements=["Basic retrieval returns results", "No evaluation in place"],
    ),
    RMMCriteria(
        level=RMMLevel.RECALL,
        name="Better Recall",
        description="Hybrid search active with Recall@5 > 70%",
        requirements=[
            "Hybrid search (dense + sparse) configured",
            "BM25 configured alongside vector search",
            "Recall@5 > 70%",
        ],
    ),
    RMMCriteria(
        level=RMMLevel.PRECISION,
        name="Better Precision",
        description="Reranker active with measurable improvement",
        requirements=[
            "Reranker active",
            "nDCG@10 shows 10%+ improvement over RMM-1",
            "HNSW parameters tuned",
        ],
    ),
    RMMCriteria(
        level=RMMLevel.TRUST,
        name="Better Trust",
        description="Guardrails active, faithfulness > 85%, citations present",
        requirements=[
            "InputGuard + OutputGuard active",
            "Faithfulness > 85%",
            "All answers include citations mapped to chunk IDs",
        ],
    ),
    RMMCriteria(
        level=RMMLevel.WORKFLOW,
        name="Better Workflow",
        description="Caching, low latency, cost tracking",
        requirements=[
            "Semantic caching active",
            "P95 latency < 4 seconds",
            "TTFT P90 < 2 seconds",
            "Cost per query tracked",
        ],
    ),
    RMMCriteria(
        level=RMMLevel.ENTERPRISE,
        name="Enterprise",
        description="Full production readiness with CI/CD gates",
        requirements=[
            "RBAC active",
            "Drift detection live",
            "CI/CD evaluation gates on every PR",
            "Adversarial tests green",
        ],
    ),
]


class RMMScorer:
    """Scores a RAG pipeline against the RAG Maturity Model.

    For Phase 1, only RMM-0 through RMM-3 are checkable. Higher levels
    require infrastructure features (caching, RBAC) not yet available.
    """

    def assess(self, metrics: dict[str, float]) -> RMMLevel:
        """Determine the RMM level based on pipeline metrics."""
        level = RMMLevel.NAIVE

        # RMM-1 (Recall): requires recall_at_k >= 0.70
        if metrics.get("recall_at_k", 0.0) >= 0.70:
            level = RMMLevel.RECALL

            # RMM-2 (Precision): requires reranker improvement
            if metrics.get("ndcg_improvement", 0.0) >= 0.10:
                level = RMMLevel.PRECISION

        # RMM-3 (Trust): requires faithfulness >= 0.85 AND context_relevance >= 0.80
        faithfulness = metrics.get("faithfulness", 0.0)
        context_relevance = metrics.get("context_relevance", 0.0)

        if faithfulness >= 0.85 and context_relevance >= 0.80:
            level = max(level, RMMLevel.TRUST)

        return level
