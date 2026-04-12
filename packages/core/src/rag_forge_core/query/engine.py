"""RAG query engine: retrieve relevant chunks → generate answer."""

from dataclasses import dataclass

from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.security.input_guard import InputGuard
from rag_forge_core.security.output_guard import OutputGuard

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
    blocked: bool = False
    blocked_reason: str | None = None


class QueryEngine:
    """Executes RAG queries using any RetrieverProtocol implementation."""

    def __init__(
        self,
        retriever: RetrieverProtocol,
        generator: GenerationProvider,
        top_k: int = 5,
        input_guard: InputGuard | None = None,
        output_guard: OutputGuard | None = None,
    ) -> None:
        self._retriever = retriever
        self._generator = generator
        self._top_k = top_k
        self._input_guard = input_guard
        self._output_guard = output_guard

    def query(self, question: str, alpha: float | None = None, user_id: str = "default") -> QueryResult:
        """Execute a RAG query. Optional alpha override for hybrid retrieval."""
        # 1. Input guard
        if self._input_guard is not None:
            guard_result = self._input_guard.check(question, user_id=user_id)
            if not guard_result.passed:
                return QueryResult(
                    answer="",
                    sources=[],
                    model_used=self._generator.model_name(),
                    chunks_retrieved=0,
                    blocked=True,
                    blocked_reason=guard_result.reason,
                )

        # 2. Retrieve
        retriever = self._retriever

        if alpha is not None and isinstance(retriever, HybridRetriever):
            retriever = HybridRetriever(
                dense=retriever._dense,
                sparse=retriever._sparse,
                alpha=alpha,
                reranker=retriever._reranker,
            )

        results = retriever.retrieve(question, self._top_k)

        if not results:
            return QueryResult(
                answer="No relevant context found for your question. Please index documents first.",
                sources=[],
                model_used=self._generator.model_name(),
                chunks_retrieved=0,
            )

        # 3. Generate
        context_text = "\n\n".join(
            f"[Source {i + 1}]: {r.text}" for i, r in enumerate(results)
        )
        user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
        answer = self._generator.generate(_SYSTEM_PROMPT, user_prompt)

        # 4. Output guard
        if self._output_guard is not None:
            chunk_ids = [r.chunk_id for r in results]
            contexts = [r.text for r in results]
            metadata_list = [dict(r.metadata) for r in results]

            output_result = self._output_guard.check(
                answer, contexts, chunk_ids=chunk_ids, contexts_metadata=metadata_list
            )
            if not output_result.passed:
                return QueryResult(
                    answer="",
                    sources=results,
                    model_used=self._generator.model_name(),
                    chunks_retrieved=len(results),
                    blocked=True,
                    blocked_reason=output_result.reason,
                )

        return QueryResult(
            answer=answer,
            sources=results,
            model_used=self._generator.model_name(),
            chunks_retrieved=len(results),
        )
