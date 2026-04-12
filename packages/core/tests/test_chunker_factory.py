"""Tests for the chunker factory."""

import pytest

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.factory import UnsupportedStrategyError, create_chunker
from rag_forge_core.chunking.fixed import FixedSizeChunker
from rag_forge_core.chunking.llm_driven import LLMDrivenChunker
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.chunking.semantic import SemanticChunker
from rag_forge_core.chunking.structural import StructuralChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.mock_generator import MockGenerator


class TestCreateChunker:
    def test_recursive_is_default(self) -> None:
        chunker = create_chunker(ChunkConfig())
        assert isinstance(chunker, RecursiveChunker)

    def test_fixed_strategy(self) -> None:
        chunker = create_chunker(ChunkConfig(strategy="fixed"))
        assert isinstance(chunker, FixedSizeChunker)

    def test_recursive_strategy(self) -> None:
        chunker = create_chunker(ChunkConfig(strategy="recursive"))
        assert isinstance(chunker, RecursiveChunker)

    def test_structural_strategy(self) -> None:
        chunker = create_chunker(ChunkConfig(strategy="structural"))
        assert isinstance(chunker, StructuralChunker)

    def test_semantic_requires_embedder(self) -> None:
        with pytest.raises(ValueError, match="embedder"):
            create_chunker(ChunkConfig(strategy="semantic"))

    def test_semantic_with_embedder(self) -> None:
        embedder = MockEmbedder()
        chunker = create_chunker(ChunkConfig(strategy="semantic"), embedder=embedder)
        assert isinstance(chunker, SemanticChunker)

    def test_llm_driven_requires_generator(self) -> None:
        with pytest.raises(ValueError, match="generator"):
            create_chunker(ChunkConfig(strategy="llm-driven"))

    def test_llm_driven_with_generator(self) -> None:
        generator = MockGenerator()
        chunker = create_chunker(ChunkConfig(strategy="llm-driven"), generator=generator)
        assert isinstance(chunker, LLMDrivenChunker)

    def test_unknown_strategy_raises(self) -> None:
        config = ChunkConfig(strategy="recursive")
        # Bypass pydantic validation by setting after init
        object.__setattr__(config, "strategy", "nonexistent")
        with pytest.raises(UnsupportedStrategyError, match="nonexistent"):
            create_chunker(config)
