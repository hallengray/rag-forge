"""Smoke tests for the RAG Maturity Model."""

from rag_forge_evaluator.maturity import RMM_CRITERIA, RMMLevel, RMMScorer


class TestRMMLevel:
    def test_all_levels_defined(self) -> None:
        assert len(RMM_CRITERIA) == 6

    def test_levels_ordered(self) -> None:
        for i, criteria in enumerate(RMM_CRITERIA):
            assert criteria.level == i

    def test_level_names(self) -> None:
        names = [c.name for c in RMM_CRITERIA]
        assert "Naive RAG" in names
        assert "Enterprise" in names

    def test_each_level_has_requirements(self) -> None:
        for criteria in RMM_CRITERIA:
            assert len(criteria.requirements) > 0


class TestRMMScorer:
    def test_default_score_is_naive(self) -> None:
        scorer = RMMScorer()
        level = scorer.assess({})
        assert level == RMMLevel.NAIVE


class TestRMMScorerLogic:
    def test_empty_metrics_returns_naive(self) -> None:
        assert RMMScorer().assess({}) == RMMLevel.NAIVE

    def test_trust_level_with_good_scores(self) -> None:
        assert RMMScorer().assess({"faithfulness": 0.90, "context_relevance": 0.85}) == RMMLevel.TRUST

    def test_trust_level_fails_with_low_faithfulness(self) -> None:
        assert RMMScorer().assess({"faithfulness": 0.70, "context_relevance": 0.85}) < RMMLevel.TRUST

    def test_trust_level_fails_with_low_relevance(self) -> None:
        assert RMMScorer().assess({"faithfulness": 0.90, "context_relevance": 0.50}) < RMMLevel.TRUST

    def test_caps_at_trust_for_phase1(self) -> None:
        metrics = {"faithfulness": 0.95, "context_relevance": 0.90, "answer_relevance": 0.90, "hallucination": 0.98}
        assert RMMScorer().assess(metrics) <= RMMLevel.TRUST
