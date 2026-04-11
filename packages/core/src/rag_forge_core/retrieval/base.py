"""Base protocol for all retriever implementations."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class RetrievalResult:
    """A single retrieval result with score and metadata."""

    chunk_id: str
    text: str
    score: float
    source_document: str
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@runtime_checkable
class RetrieverProtocol(Protocol):
    """Protocol that all retrievers must implement."""

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Retrieve the most relevant chunks for a query."""
        ...

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Index a list of chunks. Returns the number of chunks indexed."""
        ...
