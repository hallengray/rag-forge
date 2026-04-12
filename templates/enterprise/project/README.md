# Enterprise RAG Pipeline

A production-grade RAG pipeline with hybrid retrieval, security guards (InputGuard + OutputGuard), and CI/CD quality gates. Scaffolded by [RAG-Forge](https://github.com/hallengray/rag-forge).

## Features

- **Hybrid search**: BM25 sparse + dense vector retrieval with Reciprocal Rank Fusion
- **Reranking**: Cohere Rerank API for improved precision
- **Security**: InputGuard (prompt injection, PII, rate limiting) + OutputGuard (faithfulness, PII, citations)
- **CI/CD gate**: GitHub Actions workflow that blocks merges when faithfulness drops below threshold
- **Evaluation**: Pre-configured golden set, quality thresholds, and audit reports

## Prerequisites

Set your API keys as environment variables:
- `COHERE_API_KEY` — for Cohere reranking (optional)
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` — for LLM generation and evaluation

## Quick Start

1. Install dependencies: `uv sync`
2. Index documents: `rag-forge index --source ./docs --enrich --sparse-index-path .rag-forge/sparse`
3. Query with guards: `rag-forge query "your question" --strategy hybrid --input-guard --output-guard`
4. Audit: `rag-forge audit --golden-set eval/golden_set.json`

## CI/CD

The included `.github/workflows/rag-audit.yml` runs evaluation on every PR and blocks merge if quality drops.

## Configuration

Edit `src/config.py` to customize your pipeline and security settings.
