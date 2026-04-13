export const CONTENT_LAST_VERIFIED = "2026-04-13";

export const SITE = {
  name: "RAG-Forge",
  url: "https://rag-forge.vercel.app",
  github: "https://github.com/hallengray/rag-forge",
  npm: "https://www.npmjs.com/package/@rag-forge/cli",
  pypi: "https://pypi.org/project/rag-forge-core",
  docs: "https://github.com/hallengray/rag-forge#readme",
  contributing:
    "https://github.com/hallengray/rag-forge/blob/main/CONTRIBUTING.md",
  releaseNotes:
    "https://github.com/hallengray/rag-forge/blob/main/docs/release-notes/v0.1.1.md",
  author: "Femi Adedayo",
} as const;

// Launch-phase trust signals. Avoid synthetic download counts on a
// brand-new package — real numbers go here once they're real.
export const TRUST = {
  status: "v0.1.1 just shipped",
  license: "MIT",
  publishedVia: "OIDC Trusted Publishers",
  earlyAdopter: "Be one of the first 100",
} as const;

export const HERO = {
  headline: "Catch RAG failures before your users do.",
  subheadline:
    "RAG-Forge audits any RAG pipeline against the RAG Maturity Model. Detect hallucinations, retrieval bypass, silent quality regressions, and cost drift before they ship — with a single CLI that works on your existing stack.",
  installCommand: "npm install -g @rag-forge/cli",
  versionBadge: "v0.1.1 — Post-audit hardening release",
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
    stat: "0",
    label: "open-source frameworks let you score any pipeline against a maturity model with framework-agnostic CLI tooling — until now",
    source: "RAG-Forge",
    citation: {
      url: "https://github.com/hallengray/rag-forge",
      retrieved: "2026-04-13",
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

// What's new in v0.1.1 — surfaced on the landing page so visitors who
// hit the site after the launch announcement land on something concrete.
export const WHATS_NEW = {
  version: "v0.1.1",
  tagline: "Post-audit hardening release",
  date: "2026-04-13",
  highlights: [
    "Pre-run cost + time estimates so you know what an audit costs before you pay for it",
    "Configurable judge model — pick Claude Opus, GPT-4 Turbo, or any other supported model via --judge-model",
    "Skip-aware aggregation: parse failures and incomplete judge outputs no longer silently zero your scores",
    "PHI/PII redaction by default in progress streams (set RAG_FORGE_LOG_QUERIES=1 to opt in)",
    "Honest about what RAGAS does and doesn't honor — fail-loud guards on unsupported judge/evaluator combinations",
    "12 bugs fixed end-to-end after a real production audit run",
  ],
  releaseNotesUrl:
    "https://github.com/hallengray/rag-forge/blob/main/docs/release-notes/v0.1.1.md",
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
