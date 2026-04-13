# RAG-Forge

> Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in — not bolted on after deployment.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

RAG-Forge bridges the gap between **building** RAG pipelines and **knowing whether they work**. It scaffolds production-ready pipelines, runs continuous evaluation as a CI/CD gate, and assesses any existing RAG system against the **RAG Maturity Model (RMM-0 through RMM-5)**.

## Installation

**CLI (Node.js 20+):**

```bash
npm install -g @rag-forge/cli
```

**Python packages (Python 3.11+):**

```bash
pip install rag-forge-core rag-forge-evaluator rag-forge-observability
```

## Quick Start

```bash
# Scaffold a new RAG project
rag-forge init basic

cd my-rag-project

# Index your documents
rag-forge index --source ./docs

# Run evaluation
rag-forge audit --golden-set eval/golden_set.json

# Score against RAG Maturity Model
rag-forge assess --audit-report reports/audit-report.json
```

## Templates

| Template | Use Case |
|----------|----------|
| `basic` | First RAG project, simple Q&A |
| `hybrid` | Production-ready document Q&A with reranking |
| `agentic` | Multi-hop reasoning with query decomposition |
| `enterprise` | Regulated industries with full security suite |
| `n8n` | AI automation agency deployments |

## Commands

| Category | Commands |
|----------|----------|
| **Scaffolding** | `init`, `add` |
| **Ingestion** | `parse`, `chunk`, `index` |
| **Query** | `query`, `inspect` |
| **Evaluation** | `audit`, `assess`, `golden add`, `golden validate` |
| **Operations** | `report`, `cache stats`, `drift report`, `cost` |
| **Security** | `guardrails test`, `guardrails scan-pii` |
| **Integration** | `serve --mcp`, `n8n export` |

Run `rag-forge --help` for the full command reference.

## RAG Maturity Model

| Level | Name | Exit Criteria |
|-------|------|---------------|
| RMM-0 | Naive | Basic vector search works |
| RMM-1 | Better Recall | Hybrid search, Recall@5 > 70% |
| RMM-2 | Better Precision | Reranker active, nDCG@10 +10% |
| RMM-3 | Better Trust | Guardrails, faithfulness > 85% |
| RMM-4 | Better Workflow | Caching, P95 < 4s, cost tracking |
| RMM-5 | Enterprise | Drift detection, CI/CD gates, adversarial tests |

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and contribution guidelines.

## License

MIT — see [LICENSE](./LICENSE)
