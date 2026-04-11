"""BM25-based sparse retrieval using the bm25s library."""

import json
from pathlib import Path

import bm25s

from rag_forge_core.retrieval.base import RetrievalResult


class SparseRetriever:
    """BM25 sparse retriever with optional file-based persistence.

    Uses the ``bm25s`` library for efficient BM25 scoring.  An optional
    ``index_path`` enables file-based persistence: the index is saved
    automatically after :meth:`index` is called, and is loaded automatically
    on construction when the path already exists.
    """

    def __init__(self, index_path: str | None = None) -> None:
        self._index_path = index_path
        self._model: bm25s.BM25 | None = None
        self._chunk_ids: list[str] = []
        self._chunk_texts: list[str] = []
        self._source_documents: list[str] = []

        # Auto-load if a persisted index exists at the given path.
        if index_path and Path(index_path).exists():
            self.load()

    # ------------------------------------------------------------------
    # Public API (satisfies RetrieverProtocol)
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Tokenize *query*, search the BM25 index, and return scored results.

        Returns an empty list when the index has not been built yet or when
        *top_k* is zero/the corpus is empty.
        """
        if top_k <= 0:
            return []

        if self._model is None or not self._chunk_ids:
            return []

        query_tokens = bm25s.tokenize(query, show_progress=False)
        actual_top_k = min(top_k, len(self._chunk_ids))
        if actual_top_k == 0:
            return []

        results, scores = self._model.retrieve(
            query_tokens, k=actual_top_k, show_progress=False
        )

        retrieval_results: list[RetrievalResult] = []
        for i in range(actual_top_k):
            doc_idx = int(results[0, i])
            score = float(scores[0, i])
            retrieval_results.append(
                RetrievalResult(
                    chunk_id=self._chunk_ids[doc_idx],
                    text=self._chunk_texts[doc_idx],
                    score=score,
                    source_document=self._source_documents[doc_idx],
                    metadata={"retriever": "bm25"},
                )
            )

        return retrieval_results

    def index(self, chunks: list[dict[str, str]]) -> int:
        """Build BM25 index from *chunks*.  Auto-saves when ``index_path`` is set.

        Each chunk must have ``"id"`` and ``"text"`` keys.

        Returns the number of chunks indexed.
        """
        self._chunk_ids = [c["id"] for c in chunks]
        self._chunk_texts = [c["text"] for c in chunks]
        self._source_documents = [c.get("source_document", "") for c in chunks]

        corpus_tokens = bm25s.tokenize(self._chunk_texts, show_progress=False)
        self._model = bm25s.BM25()
        self._model.index(corpus_tokens, show_progress=False)

        if self._index_path:
            self.save()

        return len(chunks)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist the BM25 index and chunk metadata to disk.

        The BM25 model is saved to ``index_path`` via ``bm25s.BM25.save``.
        Chunk IDs are stored separately in ``sparse_metadata.json`` inside
        the same directory because ``bm25s`` does not preserve them.
        """
        if self._model is None or self._index_path is None:
            return

        path = Path(self._index_path)
        path.mkdir(parents=True, exist_ok=True)

        # bm25s.save expects a directory path (without trailing slash).
        self._model.save(str(path), corpus=self._chunk_texts)

        metadata_path = path / "sparse_metadata.json"
        metadata_path.write_text(
            json.dumps({"chunk_ids": self._chunk_ids, "source_documents": self._source_documents}),
            encoding="utf-8",
        )

    def load(self) -> None:
        """Load a BM25 index and chunk metadata from disk.

        Does nothing if ``index_path`` is ``None`` or the directory does not
        exist.  After loading, :meth:`retrieve` is immediately usable.
        """
        if self._index_path is None:
            return

        path = Path(self._index_path)
        if not path.exists():
            return

        # Load index only — no corpus. This ensures retrieve() returns integer
        # document indices rather than the stored corpus objects, so our own
        # _chunk_ids / _chunk_texts arrays are used for lookups.
        self._model = bm25s.BM25.load(str(path), load_corpus=False)

        metadata_path = path / "sparse_metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self._chunk_ids = metadata["chunk_ids"]
            self._chunk_texts = metadata.get("chunk_texts", [
                str(i) for i in range(len(self._chunk_ids))
            ])
            self._source_documents = metadata.get("source_documents", [""] * len(self._chunk_ids))
