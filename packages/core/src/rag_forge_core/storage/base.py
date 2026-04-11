"""Base types and protocol for vector storage."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class VectorItem:
    """An item to store in the vector database."""

    id: str
    vector: list[float]
    text: str
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A result from a vector similarity search."""

    id: str
    text: str
    score: float
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@runtime_checkable
class VectorStore(Protocol):
    """Protocol that all vector store implementations must follow."""

    def create_collection(self, name: str, dimension: int) -> None: ...

    def upsert(self, collection: str, items: list[VectorItem]) -> int: ...

    def search(
        self, collection: str, vector: list[float], top_k: int = 5
    ) -> list[SearchResult]: ...

    def count(self, collection: str) -> int: ...

    def delete_collection(self, collection: str) -> None: ...
