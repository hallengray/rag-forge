"""Embedding providers: OpenAI, local BGE-M3, and mock for testing."""

from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.embedding.mock_embedder import MockEmbedder

__all__ = ["EmbeddingProvider", "MockEmbedder"]
