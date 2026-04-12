export const SITE = {
  name: "RAG-Forge",
  url: "https://rag-forge.vercel.app",
  github: "https://github.com/hallengray/rag-forge",
  npm: "https://www.npmjs.com/package/rag-forge",
  pypi: "https://pypi.org/project/rag-forge-core",
  docs: "https://github.com/hallengray/rag-forge#readme",
  contributing:
    "https://github.com/hallengray/rag-forge/blob/main/CONTRIBUTING.md",
  author: "Femi Adedayo",
} as const;

export const TRUST = {
  githubStars: "120",
  npmDownloads: "1.2k",
  pypiDownloads: "850",
  contributors: "8",
} as const;

export const HERO = {
  headline: "Production-grade RAG pipelines with evaluation baked in.",
  subheadline:
    "RAG-Forge bridges the gap between building RAG pipelines and knowing whether they actually work. Scaffold, evaluate, and assess any pipeline against the RAG Maturity Model.",
  installCommand: "npm install -g rag-forge",
} as const;

export const PROBLEMS = [
  {
    stat: "73%",
    label: "of enterprise RAG systems are over budget",
    source: "Industry analysis, 2026",
  },
  {
    stat: "40%",
    label: "of RAG deployments lack systematic evaluation",
    source: "Industry surveys, early 2026",
  },
  {
    stat: "32%",
    label: "cite quality as the #1 deployment barrier",
    source: "LangChain State of AI Agents 2026",
  },
] as const;

export const PILLARS = [
  {
    title: "Pipeline Primitives",
    description:
      "Five chunking strategies, dense + sparse + hybrid retrieval, contextual enrichment, and reranking. Bring your own embedding model.",
    snippet: "create_chunker(ChunkConfig(strategy=\"semantic\"))",
  },
  {
    title: "Evaluation as a CI/CD Gate",
    description:
      "RAGAS, DeepEval, and LLM-as-Judge baked in. Block PRs when faithfulness drops below threshold.",
    snippet: "rag-forge audit --golden-set qa.json --threshold 0.85",
  },
  {
    title: "Built-in Observability",
    description:
      "OpenTelemetry tracing on every pipeline stage. Drift detection, cost estimation, semantic caching.",
    snippet: "rag-forge drift report --baseline baseline.json",
  },
  {
    title: "Production Templates",
    description:
      "Five battle-tested starting points. shadcn/ui model — you own every line of code.",
    snippet: "rag-forge init enterprise",
  },
] as const;

export const RMM_LEVELS = [
  {
    level: 0,
    name: "Naive",
    description: "Basic vector search works",
    criteria: "Vector retrieval returns results",
  },
  {
    level: 1,
    name: "Better Recall",
    description: "Hybrid search active, Recall@5 > 70%",
    criteria: "Dense + sparse + RRF fusion",
  },
  {
    level: 2,
    name: "Better Precision",
    description: "Reranker active, nDCG@10 +10%",
    criteria: "Cross-encoder reranking on top results",
  },
  {
    level: 3,
    name: "Better Trust",
    description: "Guardrails, faithfulness > 85%, citations",
    criteria: "InputGuard + OutputGuard active",
    highlight: true,
  },
  {
    level: 4,
    name: "Better Workflow",
    description: "Caching, P95 < 4s, cost tracking",
    criteria: "Semantic cache + telemetry + cost meter",
  },
  {
    level: 5,
    name: "Enterprise",
    description: "Drift detection, CI/CD gates, adversarial tests",
    criteria: "All audit thresholds pass",
  },
] as const;

export const QUICK_START_DEV = `# Install the CLI
npm install -g rag-forge

# Scaffold a project
rag-forge init basic

# Index your docs and run an audit
cd my-rag-project
rag-forge index --source ./docs
rag-forge audit --golden-set eval/golden_set.json`;

export const QUICK_START_AGENT = `# Run as an MCP server for Claude Code or any MCP client
rag-forge serve --mcp --port 3100

# Or via stdio for direct integration
rag-forge serve --mcp --stdio`;

export const COMPARISON = {
  rows: [
    "Framework agnostic (audit any pipeline)",
    "Evaluation built in (CI/CD gate)",
    "RAG Maturity Model scoring",
    "OpenTelemetry native",
    "MCP server",
    "CLI scaffolding",
    "Code ownership (shadcn model)",
    "Drift detection",
  ],
  values: {
    "rag-forge": [true, true, true, true, true, true, true, true],
    langchain: [false, "partial", false, "partial", false, false, false, false],
    llamaindex: [false, false, false, false, false, false, false, false],
    ragas: [true, true, false, false, false, false, false, false],
  },
} as const;

export const TEMPLATES = [
  {
    name: "basic",
    description: "First RAG project, simple Q&A",
    complexity: "Beginner",
  },
  {
    name: "hybrid",
    description: "Production-ready document Q&A with reranking",
    complexity: "Intermediate",
  },
  {
    name: "agentic",
    description: "Multi-hop reasoning with query decomposition",
    complexity: "Advanced",
  },
  {
    name: "enterprise",
    description: "Regulated industries with full security suite",
    complexity: "Advanced",
  },
  {
    name: "n8n",
    description: "AI automation agency deployments",
    complexity: "Intermediate",
  },
] as const;
