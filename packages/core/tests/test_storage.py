"""Tests for the vector storage module."""

from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.storage.base import SearchResult, VectorItem, VectorStore
from rag_forge_core.storage.qdrant import QdrantStore


class TestQdrantStore:
    def test_implements_protocol(self) -> None:
        assert isinstance(QdrantStore(), VectorStore)

    def test_create_collection(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=384)
        assert store.count("test") == 0

    def test_upsert_and_count(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        items = [
            VectorItem(id="1", vector=[0.1, 0.2, 0.3, 0.4], text="hello", metadata={}),
            VectorItem(id="2", vector=[0.5, 0.6, 0.7, 0.8], text="world", metadata={}),
        ]
        assert store.upsert("test", items) == 2
        assert store.count("test") == 2

    def test_search_returns_results(self) -> None:
        embedder = MockEmbedder(dimension=384)
        store = QdrantStore()
        store.create_collection("test", dimension=384)
        texts = ["Python is great", "JavaScript is popular", "Rust is fast"]
        vectors = embedder.embed(texts)
        items = [
            VectorItem(id=str(i), vector=v, text=t, metadata={"index": i})
            for i, (t, v) in enumerate(zip(texts, vectors))
        ]
        store.upsert("test", items)
        query_vector = embedder.embed(["Python programming"])[0]
        results = store.search("test", query_vector, top_k=2)
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    def test_delete_collection(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        store.upsert("test", [VectorItem(id="1", vector=[0.1, 0.2, 0.3, 0.4], text="hi", metadata={})])
        store.delete_collection("test")
        assert store.count("test") == 0
