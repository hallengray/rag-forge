"""Tests for the dense retriever adapter."""

from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.storage.base import VectorItem
from rag_forge_core.storage.qdrant import QdrantStore


class TestDenseRetriever:
    def _setup_store(self) -> tuple[QdrantStore, MockEmbedder]:
        """Create a store with 3 indexed documents."""
        store = QdrantStore()
        embedder = MockEmbedder(dimension=384)
        store.create_collection("test", dimension=384)
        texts = ["Python is great", "JavaScript is popular", "Rust is fast"]
        vectors = embedder.embed(texts)
        items = [
            VectorItem(
                id=str(i),
                vector=v,
                text=t,
                metadata={"source_document": f"doc{i}.md"},
            )
            for i, (t, v) in enumerate(zip(texts, vectors, strict=True))
        ]
        store.upsert("test", items)
        return store, embedder

    def test_implements_protocol(self) -> None:
        store = QdrantStore()
        embedder = MockEmbedder()
        retriever = DenseRetriever(embedder=embedder, store=store)
        assert isinstance(retriever, RetrieverProtocol)

    def test_retrieve_returns_results(self) -> None:
        store, embedder = self._setup_store()
        retriever = DenseRetriever(
            embedder=embedder, store=store, collection_name="test"
        )
        results = retriever.retrieve("Python programming", top_k=2)
        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_retrieve_result_fields(self) -> None:
        store, embedder = self._setup_store()
        retriever = DenseRetriever(
            embedder=embedder, store=store, collection_name="test"
        )
        results = retriever.retrieve("Python", top_k=1)
        result = results[0]
        assert isinstance(result.chunk_id, str)
        assert isinstance(result.text, str)
        assert isinstance(result.score, float)
        assert isinstance(result.source_document, str)

    def test_retrieve_empty_collection(self) -> None:
        store = QdrantStore()
        embedder = MockEmbedder(dimension=384)
        store.create_collection("empty", dimension=384)
        retriever = DenseRetriever(
            embedder=embedder, store=store, collection_name="empty"
        )
        results = retriever.retrieve("anything", top_k=5)
        assert results == []

    def test_retrieve_nonexistent_collection(self) -> None:
        store = QdrantStore()
        embedder = MockEmbedder(dimension=384)
        retriever = DenseRetriever(
            embedder=embedder, store=store, collection_name="nonexistent"
        )
        results = retriever.retrieve("anything", top_k=5)
        assert results == []
