export interface RagForgeConfig {
  thresholds: {
    contextRelevance: number;
    faithfulness: number;
    answerRelevance: number;
    hallucinationRate: number;
    recallAtK: number;
    latencyP95: number;
    ttftP90: number;
  };
  model: {
    embedding: string;
    generator: string;
    judge: string;
  };
  evaluation: {
    goldenSetPath: string;
    ciGateMetric: string;
    ciGateThreshold: number;
  };
}

export interface AuditInput {
  query: string;
  contexts: string[];
  response: string;
  expected_answer?: string;
  chunk_ids?: string[];
  latency_ms?: number;
  model_used?: string;
}

export interface AuditResult {
  overallScore: number;
  rmmLevel: number;
  metrics: Record<string, number>;
  recommendations: string[];
}

export type TemplateType = "basic" | "hybrid" | "agentic" | "enterprise" | "n8n";

export type ChunkStrategy =
  | "fixed"
  | "recursive"
  | "semantic"
  | "structural"
  | "llm-driven"
  | "late-chunking";
