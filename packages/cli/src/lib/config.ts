import { cosmiconfig } from "cosmiconfig";
import type { RagForgeConfig } from "../types/index.js";

const DEFAULT_CONFIG: RagForgeConfig = {
  thresholds: {
    contextRelevance: 0.8,
    faithfulness: 0.85,
    answerRelevance: 0.8,
    hallucinationRate: 0.05,
    recallAtK: 0.7,
    latencyP95: 4000,
    ttftP90: 2000,
  },
  model: {
    embedding: "text-embedding-3-large",
    generator: "claude-sonnet-4-20250514",
    judge: "claude-sonnet-4-20250514",
  },
  evaluation: {
    goldenSetPath: "eval/golden_set.json",
    ciGateMetric: "faithfulness",
    ciGateThreshold: 0.85,
  },
};

export async function loadConfig(searchFrom?: string): Promise<RagForgeConfig> {
  const explorer = cosmiconfig("rag-forge", {
    searchPlaces: [
      "rag-forge.config.ts",
      "rag-forge.config.js",
      "rag-forge.config.json",
      ".rag-forgerc.json",
    ],
  });

  const result = await explorer.search(searchFrom);

  if (!result || result.isEmpty) {
    return DEFAULT_CONFIG;
  }

  return {
    ...DEFAULT_CONFIG,
    ...(result.config as Partial<RagForgeConfig>),
    thresholds: {
      ...DEFAULT_CONFIG.thresholds,
      ...((result.config as Partial<RagForgeConfig>).thresholds ?? {}),
    },
    model: {
      ...DEFAULT_CONFIG.model,
      ...((result.config as Partial<RagForgeConfig>).model ?? {}),
    },
    evaluation: {
      ...DEFAULT_CONFIG.evaluation,
      ...((result.config as Partial<RagForgeConfig>).evaluation ?? {}),
    },
  };
}
