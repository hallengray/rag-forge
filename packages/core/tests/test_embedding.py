"""Tests for the embedding provider module."""

from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.embedding.mock_embedder import MockEmbedder


class TestMockEmbedder:
    def test_implements_protocol(self) -> None:
        assert isinstance(MockEmbedder(), EmbeddingProvider)

    def test_returns_correct_dimension(self) -> None:
        assert MockEmbedder(dimension=384).dimension() == 384

    def test_embed_returns_correct_count(self) -> None:
        assert len(MockEmbedder().embed(["hello", "world"])) == 2

    def test_embed_returns_correct_dimension(self) -> None:
        vectors = MockEmbedder(dimension=128).embed(["test"])
        assert len(vectors[0]) == 128

    def test_deterministic(self) -> None:
        e = MockEmbedder()
        assert e.embed(["hello world"]) == e.embed(["hello world"])

    def test_different_input_different_output(self) -> None:
        e = MockEmbedder()
        assert e.embed(["hello"]) != e.embed(["world"])

    def test_model_name(self) -> None:
        assert MockEmbedder().model_name() == "mock-embedder"

    def test_empty_input(self) -> None:
        assert MockEmbedder().embed([]) == []
