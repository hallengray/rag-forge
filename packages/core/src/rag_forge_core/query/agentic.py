"""Agentic query engine with multi-query decomposition."""

from __future__ import annotations

import json
import logging
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opentelemetry import trace

    from rag_forge_core.context.semantic_cache import SemanticCache
    from rag_forge_core.generation.base import GenerationProvider
    from rag_forge_core.query.engine import QueryResult
    from rag_forge_core.retrieval.base import RetrievalResult, RetrieverProtocol
    from rag_forge_core.security.input_guard import InputGuard
    from rag_forge_core.security.output_guard import OutputGuard

logger = logging.getLogger(__name__)

_DECOMPOSE_SYSTEM_PROMPT = (
    "You are a query decomposition assistant. Break the following complex "
    "question into 3-5 simpler, independent sub-questions that can each be "
    "answered by searching a document collection separately.\n\n"
    'Respond with ONLY a JSON array of strings: ["sub-question 1", "sub-question 2", ...]'
)

_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based ONLY on the "
    "provided context. If the context does not contain enough information to answer "
    "the question, say so clearly. Do not make up information."
)


class AgenticQueryEngine:
    """Multi-query decomposition engine for complex questions."""

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
        if self._tracer is not None:
            return self._tracer.start_as_current_span(name)
        return nullcontext()

    def query(self, question: str, user_id: str = "default") -> QueryResult:
        from rag_forge_core.query.engine import QueryResult

        with self._span("rag-forge.agentic_query"):
            # 1. Input guard
            if self._input_guard is not None:
                guard_result = self._input_guard.check(question, user_id=user_id)
                if not guard_result.passed:
                    return QueryResult(
                        answer="", sources=[], model_used=self._generator.model_name(),
                        chunks_retrieved=0, blocked=True, blocked_reason=guard_result.reason,
                    )

            # 2. Cache check
            if self._cache is not None:
                cached = self._cache.get(question)
                if cached is not None:
                    return cached

            # 3. Decompose
            with self._span("rag-forge.decompose") as span:
                sub_queries = self._decompose(question)
                if span is not None:
                    span.set_attribute("sub_query_count", len(sub_queries))

            # 4. Retrieve for each sub-query
            all_results: list[list[RetrievalResult]] = []
            for sub_q in sub_queries:
                with self._span("rag-forge.sub_retrieve") as span:
                    results = self._retriever.retrieve(sub_q, self._top_k)
                    all_results.append(results)
                    if span is not None:
                        span.set_attribute("sub_query", sub_q)
                        span.set_attribute("result_count", len(results))

            # 5. Merge and deduplicate
            with self._span("rag-forge.merge"):
                merged = self._merge_results(all_results)

            if not merged:
                return QueryResult(
                    answer="No relevant context found for your question.",
                    sources=[], model_used=self._generator.model_name(), chunks_retrieved=0,
                )

            # 6. Generate final answer
            context_text = "\n\n".join(f"[Source {i + 1}]: {r.text}" for i, r in enumerate(merged))
            user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"

            with self._span("rag-forge.generate") as span:
                answer = self._generator.generate(_SYSTEM_PROMPT, user_prompt)
                if span is not None:
                    span.set_attribute("model", self._generator.model_name())

            # 7. Output guard
            if self._output_guard is not None:
                chunk_ids = [r.chunk_id for r in merged]
                contexts = [r.text for r in merged]
                metadata_list = [dict(r.metadata) for r in merged]
                output_result = self._output_guard.check(
                    answer, contexts, chunk_ids=chunk_ids, contexts_metadata=metadata_list
                )
                if not output_result.passed:
                    return QueryResult(
                        answer="", sources=[], model_used=self._generator.model_name(),
                        chunks_retrieved=len(merged), blocked=True, blocked_reason=output_result.reason,
                    )

            result = QueryResult(
                answer=answer, sources=merged,
                model_used=self._generator.model_name(), chunks_retrieved=len(merged),
            )

            # 8. Cache store
            if self._cache is not None:
                self._cache.set(question, result)

            return result

    def _decompose(self, question: str) -> list[str]:
        try:
            response = self._generator.generate(_DECOMPOSE_SYSTEM_PROMPT, question)
            sub_queries = json.loads(response)
            if isinstance(sub_queries, list) and len(sub_queries) > 0:
                return [str(q) for q in sub_queries]
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Query decomposition returned invalid JSON, using original question")
        return [question]

    def _merge_results(self, results_per_query: list[list[RetrievalResult]]) -> list[RetrievalResult]:
        best: dict[str, RetrievalResult] = {}
        for results in results_per_query:
            for result in results:
                existing = best.get(result.chunk_id)
                if existing is None or result.score > existing.score:
                    best[result.chunk_id] = result
        merged = sorted(best.values(), key=lambda r: r.score, reverse=True)
        return merged[: self._top_k * 2]
