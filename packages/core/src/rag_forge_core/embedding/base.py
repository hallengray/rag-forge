"""Base protocol for embedding providers."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol that all embedding providers must implement."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        ...

    def model_name(self) -> str:
        """Return the name of the embedding model."""
        ...
