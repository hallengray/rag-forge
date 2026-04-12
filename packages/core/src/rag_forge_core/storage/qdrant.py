"""Qdrant vector store implementation."""

import contextlib

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from rag_forge_core.storage.base import SearchResult, VectorItem


class QdrantStore:
    """Vector store backed by Qdrant. Defaults to in-memory (no Docker needed)."""

    def __init__(
        self,
        location: str = ":memory:",
        url: str | None = None,
        path: str | None = None,
    ) -> None:
        if url:
            self._client = QdrantClient(url=url)
        elif path:
            self._client = QdrantClient(path=path)
        else:
            self._client = QdrantClient(location=location)

    def create_collection(self, name: str, dimension: int) -> None:
        if self._client.collection_exists(name):
            self._client.delete_collection(name)
        self._client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )

    def upsert(self, collection: str, items: list[VectorItem]) -> int:
        if not items:
            return 0
        points = [
            PointStruct(
                id=idx,
                vector=item.vector,
                payload={"text": item.text, "item_id": item.id, **item.metadata},
            )
            for idx, item in enumerate(items)
        ]
        self._client.upsert(collection_name=collection, points=points)
        return len(points)

    def search(
        self, collection: str, vector: list[float], top_k: int = 5
    ) -> list[SearchResult]:
        hits = self._client.query_points(
            collection_name=collection,
            query=vector,
            limit=top_k,
        ).points
        results: list[SearchResult] = []
        for hit in hits:
            payload = dict(hit.payload or {})
            text = str(payload.pop("text", ""))
            item_id = str(payload.pop("item_id", hit.id))
            meta = {
                k: v for k, v in payload.items() if isinstance(v, (str, int, float))
            }
            results.append(
                SearchResult(
                    id=item_id,
                    text=text,
                    score=hit.score or 0.0,
                    metadata=meta,
                )
            )
        return results

    def count(self, collection: str) -> int:
        try:
            info = self._client.get_collection(collection)
            return info.points_count or 0
        except Exception:
            return 0

    def delete_collection(self, collection: str) -> None:
        with contextlib.suppress(Exception):
            self._client.delete_collection(collection)

    def get_by_id(self, collection: str, item_id: str) -> VectorItem | None:
        """Retrieve a single chunk by its application-level UUID stored in the payload."""
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            results = self._client.scroll(
                collection_name=collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="item_id", match=MatchValue(value=item_id))]
                ),
                limit=1,
                with_vectors=False,
            )
            points = results[0]
            if not points:
                return None
            point = points[0]
            payload = dict(point.payload or {})
            text = str(payload.pop("text", ""))
            payload.pop("item_id", None)
            meta = {k: v for k, v in payload.items() if isinstance(v, (str, int, float))}
            return VectorItem(id=item_id, vector=[], text=text, metadata=meta)
        except Exception:
            return None
