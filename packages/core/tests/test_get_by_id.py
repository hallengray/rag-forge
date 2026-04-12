"""Tests for VectorStore.get_by_id()."""

from rag_forge_core.storage.base import VectorItem
from rag_forge_core.storage.qdrant import QdrantStore


class TestGetById:
    def test_get_existing_item(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        items = [
            VectorItem(id="item-1", vector=[0.1, 0.2, 0.3, 0.4], text="Hello world", metadata={"source_document": "doc.md"}),
            VectorItem(id="item-2", vector=[0.5, 0.6, 0.7, 0.8], text="Goodbye world", metadata={"source_document": "doc2.md"}),
        ]
        store.upsert("test", items)
        result = store.get_by_id("test", "item-1")
        assert result is not None
        assert result.id == "item-1"
        assert result.text == "Hello world"
        assert result.metadata["source_document"] == "doc.md"

    def test_get_missing_item(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        store.upsert("test", [VectorItem(id="item-1", vector=[0.1, 0.2, 0.3, 0.4], text="Hello", metadata={})])
        assert store.get_by_id("test", "nonexistent") is None

    def test_get_from_nonexistent_collection(self) -> None:
        store = QdrantStore()
        assert store.get_by_id("nonexistent", "item-1") is None

    def test_get_preserves_metadata(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        store.upsert("test", [
            VectorItem(id="item-1", vector=[0.1, 0.2, 0.3, 0.4], text="Test",
                       metadata={"source_document": "readme.md", "chunk_index": 3, "strategy": "recursive"}),
        ])
        result = store.get_by_id("test", "item-1")
        assert result is not None
        assert result.metadata["source_document"] == "readme.md"
        assert result.metadata["chunk_index"] == 3
