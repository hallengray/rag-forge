"""RAG query engine: retrieve relevant chunks → generate answer."""

from dataclasses import dataclass

from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol

_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based ONLY on the "
    "provided context. If the context does not contain enough information to answer "
    "the question, say so clearly. Do not make up information."
)


@dataclass
class QueryResult:
    """Result of a RAG query."""

    answer: str
    sources: list[RetrievalResult]
    model_used: str
    chunks_retrieved: int


class QueryEngine:
    """Executes RAG queries using any RetrieverProtocol implementation."""

    def __init__(
        self,
        retriever: RetrieverProtocol,
        generator: GenerationProvider,
        top_k: int = 5,
    ) -> None:
        self._retriever = retriever
        self._generator = generator
        self._top_k = top_k

    def query(self, question: str) -> QueryResult:
        """Execute a RAG query and return the generated answer with sources."""
        results = self._retriever.retrieve(question, self._top_k)

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
