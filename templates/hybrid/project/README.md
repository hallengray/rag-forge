# Hybrid RAG Pipeline

A production-ready RAG pipeline with hybrid retrieval (BM25 + vector), Cohere reranking, and contextual enrichment. Scaffolded by [RAG-Forge](https://github.com/hallengray/rag-forge).

## Features

- **Hybrid search**: BM25 sparse + dense vector retrieval with Reciprocal Rank Fusion
- **Reranking**: Cohere Rerank API for improved precision
- **Contextual enrichment**: Document-level summaries prepended to chunks for better embeddings
- **Evaluation**: Pre-configured golden set and quality thresholds

## Prerequisites

Set your API keys as environment variables:
- `COHERE_API_KEY` — for Cohere reranking (optional)
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` — for LLM generation and evaluation

## Quick Start

1. Install dependencies: `uv sync`
2. Index documents: `rag-forge index --source ./docs --enrich --sparse-index-path .rag-forge/sparse`
3. Query: `rag-forge query "your question" --strategy hybrid --sparse-index-path .rag-forge/sparse`
4. Audit: `rag-forge audit --golden-set eval/golden_set.json`

## Configuration

Edit `src/config.py` to customize your pipeline settings.
