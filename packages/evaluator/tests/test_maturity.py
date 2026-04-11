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
