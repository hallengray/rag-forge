"""RAG query engine: retrieve relevant chunks → generate answer."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from opentelemetry import trace

from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
from rag_forge_core.retrieval.hybrid import HybridRetriever
from rag_forge_core.security.input_guard import InputGuard
from rag_forge_core.security.output_guard import OutputGuard

if TYPE_CHECKING:
    from rag_forge_core.context.semantic_cache import SemanticCache

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
        tracer: trace.Tracer | None = None,
        cache: SemanticCache | None = None,
    ) -> None:
        self._retriever = retriever
        self._generator = generator
        self._top_k = top_k
        self._input_guard = input_guard
        self._output_guard = output_guard
        self._tracer = tracer
        self._cache = cache

    def _span(self, name: str) -> Any:
        """Return an active span context manager, or a no-op if no tracer is configured."""
        if self._tracer is not None:
            return self._tracer.start_as_current_span(name)
        return nullcontext()

    def query(self, question: str, alpha: float | None = None, user_id: str = "default") -> QueryResult:
        """Execute a RAG query. Optional alpha override for hybrid retrieval."""
        with self._span("rag-forge.query"):
            # 0. Cache check
            if self._cache is not None:
                cached = self._cache.get(question)
                if cached is not None:
                    with self._span("rag-forge.cache_hit") as span:
                        if span is not None:
                            span.set_attribute("cache_hit", True)
                    return cached

            # 1. Input guard
            if self._input_guard is not None:
                with self._span("rag-forge.input_guard") as span:
                    guard_result = self._input_guard.check(question, user_id=user_id)
                    if span is not None:
                        span.set_attribute("passed", guard_result.passed)
                        span.set_attribute("blocked_by", guard_result.reason or "")
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

            with self._span("rag-forge.retrieve") as span:
                results = retriever.retrieve(question, self._top_k)
                if span is not None:
                    span.set_attribute("result_count", len(results))
                    span.set_attribute("top_k", self._top_k)

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
            with self._span("rag-forge.generate") as span:
                answer = self._generator.generate(_SYSTEM_PROMPT, user_prompt)
                if span is not None:
                    span.set_attribute("model", self._generator.model_name())

            # 4. Output guard
            if self._output_guard is not None:
                chunk_ids = [r.chunk_id for r in results]
                contexts = [r.text for r in results]
                metadata_list = [dict(r.metadata) for r in results]

                with self._span("rag-forge.output_guard") as span:
                    output_result = self._output_guard.check(
                        answer, contexts, chunk_ids=chunk_ids, contexts_metadata=metadata_list
                    )
                    if span is not None:
                        span.set_attribute("passed", output_result.passed)
                        faithfulness = getattr(output_result, "faithfulness_score", None)
                        if faithfulness is not None:
                            span.set_attribute("faithfulness_score", faithfulness)
                    if not output_result.passed:
                        return QueryResult(
                            answer="",
                            sources=[],
                            model_used=self._generator.model_name(),
                            chunks_retrieved=len(results),
                            blocked=True,
                            blocked_reason=output_result.reason,
                        )

            result = QueryResult(
                answer=answer,
                sources=results,
                model_used=self._generator.model_name(),
                chunks_retrieved=len(results),
            )

            if self._cache is not None:
                self._cache.set(question, result)

            return result
