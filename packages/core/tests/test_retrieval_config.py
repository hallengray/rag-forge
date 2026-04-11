"""Tests for retrieval configuration validation."""

import pytest
from pydantic import ValidationError

from rag_forge_core.retrieval.config import RerankerType, RetrievalConfig, RetrievalStrategy


class TestRetrievalStrategy:
    def test_dense_is_default(self) -> None:
        config = RetrievalConfig()
        assert config.strategy == RetrievalStrategy.DENSE

    def test_valid_strategies(self) -> None:
        for strategy in ("dense", "sparse", "hybrid"):
            config = RetrievalConfig(strategy=strategy)
            assert config.strategy == RetrievalStrategy(strategy)

    def test_invalid_strategy_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(strategy="invalid")


class TestAlpha:
    def test_default_alpha(self) -> None:
        config = RetrievalConfig()
        assert config.alpha == 0.6

    def test_alpha_bounds(self) -> None:
        RetrievalConfig(alpha=0.0)
        RetrievalConfig(alpha=1.0)

    def test_alpha_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(alpha=-0.1)

    def test_alpha_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(alpha=1.1)


class TestReranker:
    def test_default_reranker_is_none(self) -> None:
        config = RetrievalConfig()
        assert config.reranker == RerankerType.NONE

    def test_valid_reranker_types(self) -> None:
        for reranker in ("none", "bge-local"):
            config = RetrievalConfig(reranker=reranker)
            assert config.reranker == RerankerType(reranker)
        # Cohere requires an API key
        config = RetrievalConfig(reranker="cohere", cohere_api_key="test-key")
        assert config.reranker == RerankerType.COHERE

    def test_invalid_reranker_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(reranker="invalid")

    def test_cohere_reranker_requires_api_key(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(reranker="cohere")

    def test_cohere_reranker_with_api_key_succeeds(self) -> None:
        config = RetrievalConfig(reranker="cohere", cohere_api_key="test-key")
        assert config.reranker == RerankerType.COHERE


class TestTopK:
    def test_default_top_k(self) -> None:
        config = RetrievalConfig()
        assert config.top_k == 5

    def test_top_k_minimum(self) -> None:
        config = RetrievalConfig(top_k=1)
        assert config.top_k == 1

    def test_top_k_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(top_k=0)

    def test_top_k_over_100_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalConfig(top_k=101)


class TestSparseIndexPath:
    def test_default_sparse_index_path_is_none(self) -> None:
        config = RetrievalConfig()
        assert config.sparse_index_path is None

    def test_custom_sparse_index_path(self) -> None:
        config = RetrievalConfig(sparse_index_path="/tmp/bm25-index")
        assert config.sparse_index_path == "/tmp/bm25-index"
