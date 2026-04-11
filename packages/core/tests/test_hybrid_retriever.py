"""Tests for hybrid retriever with Reciprocal Rank Fusion."""

from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.retrieval.reranker import MockReranker
from rag_forge_core.retrieval.sparse import SparseRetriever
from rag_forge_core.storage.base import VectorItem
from rag_forge_core.storage.qdrant import QdrantStore

SAMPLE_TEXTS = [
    "Python is a popular programming language for data science",
    "JavaScript powers interactive web applications",
    "Rust provides memory safety without garbage collection",
    "Python machine learning uses libraries like scikit-learn",
    "TypeScript adds static typing to JavaScript code",
]


def _build_retrievers() -> tuple[DenseRetriever, SparseRetriever]:
    """Build dense + sparse retrievers with the same corpus."""
    embedder = MockEmbedder(dimension=384)
    store = QdrantStore()
    store.create_collection("test", dimension=384)

    vectors = embedder.embed(SAMPLE_TEXTS)
    items = [
        VectorItem(
            id=f"chunk-{i}",
            vector=v,
            text=t,
            metadata={"source_document": f"doc{i}.md"},
        )
        for i, (t, v) in enumerate(zip(SAMPLE_TEXTS, vectors, strict=True))
    ]
    store.upsert("test", items)

    dense = DenseRetriever(embedder=embedder, store=store, collection_name="test")

    sparse = SparseRetriever()
    sparse.index([{"id": f"chunk-{i}", "text": t} for i, t in enumerate(SAMPLE_TEXTS)])

    return dense, sparse


class TestHybridRetriever:
    def test_implements_protocol(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        assert isinstance(hybrid, RetrieverProtocol)

    def test_retrieve_returns_results(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        results = hybrid.retrieve("Python programming", top_k=3)
        assert len(results) > 0
        assert len(results) <= 3
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_results_sorted_by_score_descending(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        results = hybrid.retrieve("Python", top_k=5)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_no_duplicate_chunk_ids(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        results = hybrid.retrieve("Python programming", top_k=5)
        chunk_ids = [r.chunk_id for r in results]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_alpha_1_is_pure_dense(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse, alpha=1.0)
        hybrid_results = hybrid.retrieve("Python", top_k=3)
        dense_results = dense.retrieve("Python", top_k=3)
        assert [r.chunk_id for r in hybrid_results] == [
            r.chunk_id for r in dense_results
        ]

    def test_alpha_0_is_pure_sparse(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse, alpha=0.0)
        hybrid_results = hybrid.retrieve("Python", top_k=3)
        sparse_results = sparse.retrieve("Python", top_k=3)
        assert [r.chunk_id for r in hybrid_results] == [
            r.chunk_id for r in sparse_results
        ]

    def test_respects_top_k(self) -> None:
        dense, sparse = _build_retrievers()
        hybrid = HybridRetriever(dense=dense, sparse=sparse)
        results = hybrid.retrieve("Python", top_k=2)
        assert len(results) <= 2


class TestHybridRetrieverWithReranker:
    def test_reranker_is_applied(self) -> None:
        dense, sparse = _build_retrievers()
        reranker = MockReranker()
        hybrid = HybridRetriever(
            dense=dense, sparse=sparse, reranker=reranker
        )
        results_no_rerank = HybridRetriever(
            dense=dense, sparse=sparse
        ).retrieve("Python", top_k=3)
        results_with_rerank = hybrid.retrieve("Python", top_k=3)

        # MockReranker reverses order, so results should differ
        ids_no_rerank = [r.chunk_id for r in results_no_rerank]
        ids_with_rerank = [r.chunk_id for r in results_with_rerank]
        assert ids_no_rerank != ids_with_rerank or len(ids_no_rerank) <= 1
