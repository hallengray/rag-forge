# RAG-Forge Architecture

## System Overview

RAG-Forge is structured as a polyglot monorepo with five core packages, each serving a distinct concern.

```
User → rag-forge CLI (TypeScript)
           │
           ├── init/add → Template Engine → Generated Project
           │
           ├── index/query → Python Bridge → packages/core (Python)
           │                                      │
           │                                      ├── Chunking Engine
           │                                      ├── Retrieval Engine (Dense + Sparse + Rerank)
           │                                      ├── Context Manager
           │                                      └── Security (InputGuard + OutputGuard)
           │
           ├── audit/assess → Python Bridge → packages/evaluator (Python)
           │                                      │
           │                                      ├── RAGAS v2 Metrics
           │                                      ├── DeepEval Metrics
           │                                      ├── LLM-as-Judge
           ��                                      ├── RMM Scorer (Maturity Model)
           │                                      └── Report Generator (HTML/PDF)
           │
           └── serve --mcp → packages/mcp (TypeScript)
                                 │
                                 └── MCP Tools (query, ingest, audit, inspect, status)
```

## CLI-to-Python Bridge

The TypeScript CLI delegates heavy computation to Python packages by spawning subprocesses via `uv run python -m <module>`. Communication uses JSON over stdout/stderr. This is the same pattern used by Prisma (Node.js CLI → Rust engine).

## Evaluation Pipeline

Every scaffolded project ships with evaluation configured from day one. The `rag-forge audit` command:

1. Loads telemetry data (JSONL) or golden set
2. Runs evaluation metrics (RAGAS + DeepEval)
3. Scores against the RAG Maturity Model (RMM-0 to RMM-5)
4. Generates a standalone HTML report (Lighthouse-style)
5. Optionally generates PDF via Playwright
