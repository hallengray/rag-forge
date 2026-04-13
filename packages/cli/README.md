# @rag-forge/cli

> Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in.

`rag-forge` is the command-line interface to RAG-Forge, a polyglot toolkit for building, evaluating, and auditing Retrieval-Augmented Generation pipelines. It scaffolds new projects, indexes documents, runs hybrid retrieval, scores pipeline output against the RAG Maturity Model (RMM), and ships every report as HTML, JSON, or PDF.

**Built for the moment your "demo works on my laptop" RAG meets a real production workload.**

## Install

```bash
npm install -g @rag-forge/cli
# or
pnpm add -g @rag-forge/cli
```

The CLI delegates pipeline and evaluation work to Python packages. Install them in a dedicated venv:

```bash
mkdir -p ~/.rag-forge && cd ~/.rag-forge
uv venv && source .venv/bin/activate
uv pip install rag-forge-core rag-forge-evaluator rag-forge-observability
```

Verify:

```bash
rag-forge --version
rag-forge-eval --help
```

## Quick start

```bash
# Scaffold a new RAG project
rag-forge init basic my-rag-project
cd my-rag-project

# Index your documents
rag-forge index --source ./docs

# Run an audit against a golden set
rag-forge audit --golden-set eval/golden_set.json --judge claude
```

The audit command prints a pre-run banner with sample count, judge model, total judge calls, estimated time, and estimated USD cost — and asks for confirmation (auto-confirmed when invoked through the npm CLI). Per-sample progress streams to stderr as the run proceeds, and a summary line shows scored count, skipped count, RMM level, and report path on completion.

## Core commands

| Command | What it does |
|---|---|
| `rag-forge init <template>` | Scaffold a new project from a template (basic, hybrid, agentic, enterprise, n8n) |
| `rag-forge index --source <dir>` | Chunk and embed a directory of documents into your vector store |
| `rag-forge query "<question>"` | Run a single RAG query end-to-end against the indexed corpus |
| `rag-forge audit` | Score pipeline output against metrics + the RAG Maturity Model |
| `rag-forge cost` | Estimate audit costs for any judge / evaluator combination |
| `rag-forge drift report` | Compare current run against a saved baseline |
| `rag-forge golden add` | Add entries to your golden question/answer set |
| `rag-forge guardrails test` | Run input/output guardrails against a test corpus |
| `rag-forge serve --mcp` | Start as an MCP server for Claude Desktop or any MCP client |
| `rag-forge inspect` | Inspect indexed chunks, embeddings, and retrieval results |

Run `rag-forge <command> --help` for full options on any command.

## The RAG Maturity Model

RAG-Forge scores every audit against a 6-level maturity model (RMM-0 through RMM-5):

| Level | Theme | Exit criterion |
|---|---|---|
| **0 — Naive** | Vector search returns results | Basic retrieval works |
| **1 — Better Recall** | Hybrid search + RRF fusion | Recall@5 > 70% |
| **2 — Better Precision** | Cross-encoder reranking | nDCG@10 +10% |
| **3 — Better Trust** | Faithfulness, citations, guardrails | Faithfulness > 85% |
| **4 — Better Workflow** | Caching, cost tracking, P95 budgets | Cache hit rate, cost meter active |
| **5 — Enterprise** | Drift detection, CI/CD gates, adversarial tests | All audit thresholds pass |

The audit command tells you which level you're at and what specifically you need to do to move up.

## Bring your own everything

- **LLM provider:** Anthropic, OpenAI, Gemini, Cohere, Bedrock, Ollama, vLLM, or any model behind your own gateway. The `JudgeProvider` protocol is two methods.
- **Vector store:** Qdrant, pgvector, Pinecone, Weaviate, Chroma, or any store implementing the `VectorStore` protocol.
- **Embedding model:** OpenAI, Cohere, sentence-transformers, BGE, or any model exposing an `embed_documents()` method.
- **Reranker:** Cohere, BGE, ColBERT, or skip reranking entirely.

Configure once in `rag-forge.config.ts` at your project root, then every command honors your choices.

## Documentation

- **Full docs:** [github.com/hallengray/rag-forge](https://github.com/hallengray/rag-forge#readme)
- **Issues:** [github.com/hallengray/rag-forge/issues](https://github.com/hallengray/rag-forge/issues)
- **Release notes:** [docs/release-notes](https://github.com/hallengray/rag-forge/tree/main/docs/release-notes)

## License

MIT — Femi Adedayo
