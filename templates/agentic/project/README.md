# Agentic RAG Pipeline

A multi-hop RAG pipeline with automatic query decomposition. Scaffolded by [RAG-Forge](https://github.com/hallengray/rag-forge).

## Features

- **Multi-query decomposition**: Complex questions broken into sub-questions automatically
- **Independent retrieval**: Each sub-question retrieves chunks independently
- **Result merging**: Chunks deduplicated and ranked across all sub-queries

## Prerequisites

Set your API keys:
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` — for LLM generation and decomposition

## Quick Start

1. Install: `uv sync`
2. Index: `rag-forge index --source ./docs`
3. Query: `rag-forge query "your complex question" --agent-mode`
4. Audit: `rag-forge audit --golden-set eval/golden_set.json`
