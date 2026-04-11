"""RAG query engine: embed question → search vectors → generate answer."""

from dataclasses import dataclass

from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.storage.base import SearchResult, VectorStore

_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based ONLY on the "
    "provided context. If the context does not contain enough information to answer "
    "the question, say so clearly. Do not make up information."
)


@dataclass
class QueryResult:
    """Result of a RAG query."""

    answer: str
    sources: list[SearchResult]
    model_used: str
    chunks_retrieved: int


class QueryEngine:
    """Executes RAG queries: embed → search → generate."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        generator: GenerationProvider,
        collection_name: str = "rag-forge",
        top_k: int = 5,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._generator = generator
        self._collection_name = collection_name
        self._top_k = top_k

    def query(self, question: str) -> QueryResult:
        """Execute a RAG query and return the generated answer with sources."""
        query_vector = self._embedder.embed([question])[0]
        try:
            results = self._store.search(self._collection_name, query_vector, self._top_k)
        except (ValueError, KeyError):
            # Collection does not exist — no documents have been indexed yet.
            results = []

        if not results:
            return QueryResult(
                answer="No relevant context found for your question. Please index documents first.",
                sources=[],
                model_used=self._generator.model_name(),
                chunks_retrieved=0,
            )

        context_text = "\n\n".join(
            f"[Source {i + 1}]: {r.text}" for i, r in enumerate(results)
        )
        user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
        answer = self._generator.generate(_SYSTEM_PROMPT, user_prompt)

        return QueryResult(
            answer=answer,
            sources=results,
            model_used=self._generator.model_name(),
            chunks_retrieved=len(results),
        )
