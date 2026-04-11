"""Dense retriever: wraps EmbeddingProvider + VectorStore into RetrieverProtocol."""

from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.storage.base import VectorStore


class DenseRetriever:
    """Adapts EmbeddingProvider + VectorStore to the RetrieverProtocol interface."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection_name: str = "rag-forge",
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._collection_name = collection_name

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Embed query, search vector store, return RetrievalResults."""
        query_vector = self._embedder.embed([query])[0]
        try:
            search_results = self._store.search(
                self._collection_name, query_vector, top_k
            )
        except (ValueError, KeyError):
            return []

        return [
            RetrievalResult(
                chunk_id=r.id,
                text=r.text,
                score=r.score,
                source_document=str(r.metadata.get("source_document", "")),
                metadata=r.metadata,
            )
            for r in search_results
        ]

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Not used — dense indexing goes through IngestionPipeline."""
        raise NotImplementedError(
            "Dense indexing is handled by IngestionPipeline, not DenseRetriever."
        )
