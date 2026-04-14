<div align="center">

# RAG-Forge

**Production-grade RAG pipelines with evaluation baked in — not bolted on after deployment.**

[![npm version](https://img.shields.io/npm/v/@rag-forge/cli?label=%40rag-forge%2Fcli)](https://www.npmjs.com/package/@rag-forge/cli)
[![PyPI version](https://img.shields.io/pypi/v/rag-forge-core?label=rag-forge-core)](https://pypi.org/project/rag-forge-core/)
[![CI](https://img.shields.io/github/actions/workflow/status/hallengray/rag-forge/ci.yml?branch=main)](https://github.com/hallengray/rag-forge/actions)
[![License: MIT](https://img.shields.io/github/license/hallengray/rag-forge)](./LICENSE)
[![Discussions](https://img.shields.io/github/discussions/hallengray/rag-forge)](https://github.com/hallengray/rag-forge/discussions)

[Docs](https://rag-forge-docs.vercel.app/) · [Website](https://rag-forge-site.vercel.app/) · [Discussions](https://github.com/hallengray/rag-forge/discussions) · [Changelog](./docs/release-notes)

</div>

---

## Why RAG-Forge?

Most RAG projects ship without evaluation, and most evaluation libraries don't help you build the pipeline. Nobody scores maturity — so teams don't know if they're at "a demo that sometimes works" or "a system you can put in front of customers."

- **Building a RAG pipeline is easy. Knowing whether it works is hard.** RAG-Forge closes that loop.
- **Eval is a first-class citizen, not an afterthought.** Every template ships with a golden set and an audit gate.
- **The RAG Maturity Model (RMM-0 → RMM-5)** gives you a concrete scorecard for any RAG system — yours or someone else's.

RAG-Forge is the only toolkit that scaffolds production-ready RAG pipelines, runs continuous evaluation as a CI/CD gate, and scores any existing system against a published maturity model.

---

## RAG Maturity Model

The RMM is the scoring framework at the heart of RAG-Forge. Run `rag-forge assess` on any audit report to see where your system sits.

| Level | Name              | Exit Criteria                                              |
|-------|-------------------|------------------------------------------------------------|
| RMM-0 | Naive             | Basic vector search works                                  |
| RMM-1 | Better Recall     | Hybrid search, Recall@5 > 70%                              |
| RMM-2 | Better Precision  | Reranker active, nDCG@10 +10%                              |
| RMM-3 | Better Trust      | Guardrails, faithfulness > 85%                             |
| RMM-4 | Better Workflow   | Caching, P95 < 4s, cost tracking                           |
| RMM-5 | Enterprise        | Drift detection, CI/CD gates, adversarial tests            |

---

## Quick Start

```bash
npm install -g @rag-forge/cli

rag-forge init basic my-rag-project
cd my-rag-project

rag-forge index --source ./docs
rag-forge audit --golden-set eval/golden_set.json
rag-forge assess --audit-report reports/audit-report.json
```

Three commands to go from empty directory to a scored RAG system with a golden set and an audit report.

---

## Installation

**CLI (Node.js 20+):**

```bash
npm install -g @rag-forge/cli
```

**Python packages (Python 3.11+):**

```bash
pip install rag-forge-core rag-forge-evaluator rag-forge-observability
```

---

## Templates

| Template     | Use Case                                             |
|--------------|------------------------------------------------------|
| `basic`      | First RAG project, simple Q&A                        |
| `hybrid`     | Production-ready document Q&A with reranking         |
| `agentic`    | Multi-hop reasoning with query decomposition         |
| `enterprise` | Regulated industries with full security suite        |
| `n8n`        | AI automation agency deployments                     |

Templates generate editable source code in your project — not framework dependencies. Fork the code, not the abstraction.

---

## Commands

| Category         | Commands                                                             |
|------------------|----------------------------------------------------------------------|
| **Scaffolding**  | `init`, `add`                                                        |
| **Ingestion**    | `parse`, `chunk`, `index`                                            |
| **Query**        | `query`, `inspect`                                                   |
| **Evaluation**   | `audit`, `assess`, `golden add`, `golden validate`                   |
| **Operations**   | `report`, `cache stats`, `drift report`, `cost`                      |
| **Security**     | `guardrails test`, `guardrails scan-pii`                             |
| **Integration**  | `serve --mcp`, `n8n export`                                          |

Run `rag-forge --help` for the full command reference.

---

## How RAG-Forge compares

There are great tools in this space. Here's an honest look at where each fits.

| Capability                        | RAG-Forge | RAGAS  | LangChain Eval | Giskard |
|-----------------------------------|:---------:|:------:|:--------------:|:-------:|
| Scaffolds a RAG pipeline          |     ✓     |   —    |       —        |    —    |
| Evaluation metrics                |     ✓     |   ✓    |       ✓        |    ✓    |
| Maturity scoring (RMM-0 → 5)      |     ✓     |   —    |       —        |    —    |
| CI gate workflow (audit action)   |     ✓     |   —    |    partial     | partial |
| MCP server                        |     ✓     |   —    |       —        |    —    |
| Guardrails / PII scanning         |     ✓     |   —    |    partial     |    ✓    |
| Drift detection                   |     ✓     |   —    |       —        | partial |
| Multi-language (TS + Python)      |     ✓     |   —    |       ✓        |    —    |
| Framework-agnostic                |     ✓     |   ✓    |       —        |    ✓    |

**Peer strengths worth knowing:**

- **RAGAS** has deeper metric research and a large community. RAG-Forge's evaluator supports RAGAS metrics — run `rag-forge audit --metrics ragas` to use them directly.
- **LangChain Eval** has the broadest ecosystem of integrations if you're already invested in LangChain.
- **Giskard** has a strong general-purpose ML testing story beyond RAG.

Pick the tool that matches your stage. RAG-Forge's wedge is the full lifecycle — scaffold → evaluate → score → ship — in one CLI, with the RMM as the objective function.

---

## Architecture

RAG-Forge is a polyglot monorepo. The CLI and MCP server are TypeScript; all RAG logic is Python. The CLI delegates to Python via a subprocess bridge so the two halves can be developed and versioned independently.

```text
rag-forge/
├── packages/
│   ├── cli/              TypeScript — Commander.js CLI (rag-forge command)
│   ├── mcp/              TypeScript — MCP server (@modelcontextprotocol/sdk)
│   ├── core/             Python    — RAG pipeline primitives
│   ├── evaluator/        Python    — RAGAS + DeepEval + LLM-as-Judge
│   └── observability/    Python    — OpenTelemetry + Langfuse
├── templates/            Project templates (basic, hybrid, agentic, enterprise, n8n)
└── apps/site/            Docs and marketing site (Next.js, deployed to Vercel)
```

See [docs/architecture.md](./docs/architecture.md) for a deeper dive.

---

## Docs & Community

- 📚 **Docs:** https://rag-forge-docs.vercel.app/
- 🌐 **Website:** https://rag-forge-site.vercel.app/
- 💬 **Discussions:** https://github.com/hallengray/rag-forge/discussions
- 🔒 **Security:** see [SECURITY.md](./SECURITY.md)
- 📝 **Changelog:** [docs/release-notes](./docs/release-notes)

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and contribution guidelines. All contributors are expected to follow our [Code of Conduct](./CODE_OF_CONDUCT.md).

---

## License

MIT — see [LICENSE](./LICENSE)
