export const CONTENT_LAST_VERIFIED = "2026-04-14";

export const SITE = {
  name: "RAG-Forge",
  url: "https://rag-forge-site.vercel.app",
  github: "https://github.com/hallengray/rag-forge",
  npm: "https://www.npmjs.com/package/@rag-forge/cli",
  pypi: "https://pypi.org/project/rag-forge-core",
  docs: "https://rag-forge-docs.vercel.app/",
  contributing:
    "https://github.com/hallengray/rag-forge/blob/main/CONTRIBUTING.md",
  releaseNotes:
    "https://github.com/hallengray/rag-forge/blob/main/docs/release-notes/v0.1.3.md",
  author: "Femi Adedayo",
} as const;

// Launch-phase trust signals. Avoid synthetic download counts on a
// brand-new package — real numbers go here once they're real.
export const TRUST = {
  status: "v0.1.3 just shipped",
  license: "MIT",
  publishedVia: "OIDC Trusted Publishers",
  earlyAdopter: "Be one of the first 100",
} as const;

export const HERO = {
  headline: "Catch RAG failures before your users do.",
  subheadline:
    "RAG-Forge audits any RAG pipeline against the RAG Maturity Model. Detect hallucinations, retrieval bypass, silent quality regressions, and cost drift before they ship — with a single CLI that works on your existing stack.",
  installCommand: "npm install -g @rag-forge/cli",
  versionBadge: "v0.1.3 — Audit resilience",
} as const;

export type Citation = {
  url: string;
  retrieved: string;
} | null;

export type ProblemStat = {
  stat: string;
  label: string;
  source: string;
  citation: Citation;
};

export const PROBLEMS: readonly ProblemStat[] = [
  {
    stat: "32%",
    label: "of teams cite quality as the #1 GenAI deployment barrier",
    source: "LangChain State of AI Agents 2026",
    citation: {
      url: "https://www.langchain.com/stateofaiagents",
      retrieved: "2026-04-13",
    },
  },
  {
    stat: "RMM-0",
    label: "is where most production RAG pipelines actually sit — naive vector search with no quality framework",
    source: "RAG-Forge Maturity Model",
    citation: {
      url: "https://github.com/hallengray/rag-forge#rag-maturity-model",
      retrieved: "2026-04-13",
    },
  },
  {
    stat: "Few",
    label: "open-source frameworks score any pipeline against a maturity model with framework-agnostic CLI tooling — RAG-Forge is one of them",
    source: "RAG-Forge",
    citation: {
      url: "https://github.com/hallengray/rag-forge",
      retrieved: "2026-04-14",
    },
  },
];

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
      "RAGAS, DeepEval, and LLM-as-Judge baked in. Cost + time estimates before each run, skip-aware aggregation, configurable thresholds in rag-forge.config.ts.",
    snippet: "rag-forge audit --golden-set qa.json --judge claude",
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

export type RmmLevel = {
  level: number;
  name: string;
  description: string;
  criteria: string;
  highlight?: boolean;
};

export const RMM_LEVELS: readonly RmmLevel[] = [
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
];

export const QUICK_START_DEV = `# Install the CLI
npm install -g @rag-forge/cli

# Scaffold a project (use --directory to name the folder)
rag-forge init basic --directory my-rag-project
cd my-rag-project

# Drop your documents into a folder of your choice
mkdir docs
echo "RAG-Forge is a CLI for building and evaluating RAG pipelines." > docs/example.md

# Index your docs and run an audit
rag-forge index --source ./docs
rag-forge audit --golden-set eval/golden_set.json`;

export const QUICK_START_AGENT = `# Run as an MCP server for Claude Code or any MCP client
rag-forge serve --mcp --port 3100

# Or via stdio for direct integration
rag-forge serve --mcp --stdio`;

export const COMPARISON_LAST_VERIFIED = "2026-04";

export const COMPARISON_CITATIONS: Readonly<Record<string, Citation>> = {
  langchain: {
    url: "https://python.langchain.com/docs/introduction/",
    retrieved: "2026-04-13",
  },
  llamaindex: {
    url: "https://docs.llamaindex.ai/en/stable/",
    retrieved: "2026-04-13",
  },
  ragas: {
    url: "https://docs.ragas.io/en/stable/",
    retrieved: "2026-04-13",
  },
};

// What's new in v0.1.3 — surfaced on the landing page so visitors who
// hit the site after the launch announcement land on something concrete.
export const WHATS_NEW = {
  version: "v0.1.3",
  tagline: "Audit resilience — partial reports and configurable retry budget",
  date: "2026-04-13",
  highlights: [
    "Partial audit-report.partial.json on mid-loop abort — never lose progress from a crash, Ctrl+C, or sustained overload",
    "Configurable RAG_FORGE_JUDGE_OVERLOAD_BUDGET_SECONDS (default 300s) so long audits survive sustained Anthropic capacity events",
    "Real-time 529 retry notices stream to stderr so long-running audits never look frozen",
    "New exit code 3 for partial audits — CI scripts can branch on partial vs hard failure vs clean run",
    "OverloadBudgetExhaustedError wraps the underlying 529 with actionable fallback options",
    "Dual-surface partial reports — top-level metrics null for screenshot safety, subset aggregates namespaced with caveats",
  ],
  releaseNotesUrl:
    "https://github.com/hallengray/rag-forge/blob/main/docs/release-notes/v0.1.3.md",
} as const;

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
    llamaindex: ["partial", "partial", false, false, false, "partial", false, false],
    ragas: [true, true, false, false, false, false, false, false],
  },
  peerStrengths: [
    {
      name: "RAGAS",
      detail:
        "Deeper metric research and a larger community. RAG-Forge's evaluator supports RAGAS as a backend — `rag-forge audit --evaluator ragas`.",
    },
    {
      name: "LangChain & LlamaIndex",
      detail:
        "Far broader integration ecosystems if you're already invested in their framework. RAG-Forge complements them by sitting on top of any pipeline.",
    },
    {
      name: "Giskard",
      detail: "Strong general-purpose ML testing story beyond RAG.",
    },
  ],
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
