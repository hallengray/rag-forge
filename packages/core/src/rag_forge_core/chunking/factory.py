"""Factory function for creating chunker instances by strategy name."""

from rag_forge_core.chunking.base import ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.generation.base import GenerationProvider


class UnsupportedStrategyError(ValueError):
    """Raised when an unknown chunking strategy is requested."""


def create_chunker(
    config: ChunkConfig,
    embedder: EmbeddingProvider | None = None,
    generator: GenerationProvider | None = None,
) -> ChunkStrategy:
    """Create a chunker instance for the given strategy.

    Args:
        config: Chunk configuration with strategy name.
        embedder: Required for "semantic" strategy.
        generator: Required for "llm-driven" strategy.

    Returns:
        A ChunkStrategy instance ready to use.

    Raises:
        ValueError: If a required dependency is missing.
        UnsupportedStrategyError: If the strategy name is unknown.
    """
    strategy = config.strategy

    if strategy == "recursive":
        from rag_forge_core.chunking.recursive import RecursiveChunker

        return RecursiveChunker(config)

    if strategy == "fixed":
        from rag_forge_core.chunking.fixed import FixedSizeChunker

        return FixedSizeChunker(config)

    if strategy == "structural":
        from rag_forge_core.chunking.structural import StructuralChunker

        return StructuralChunker(config)

    if strategy == "semantic":
        if embedder is None:
            msg = "Semantic chunking requires an embedder. Pass embedder= to create_chunker()."
            raise ValueError(msg)
        from rag_forge_core.chunking.semantic import SemanticChunker

        return SemanticChunker(config=config, embedder=embedder)

    if strategy == "llm-driven":
        if generator is None:
            msg = (
                "LLM-driven chunking requires a generator. "
                "Pass generator= to create_chunker()."
            )
            raise ValueError(msg)
        from rag_forge_core.chunking.llm_driven import LLMDrivenChunker

        return LLMDrivenChunker(config=config, generator=generator)

    raise UnsupportedStrategyError(
        f"Unknown chunking strategy: {strategy!r}. "
        "Supported: 'recursive', 'fixed', 'structural', 'semantic', 'llm-driven'."
    )
