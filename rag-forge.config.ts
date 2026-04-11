/**
 * RAG-Forge default configuration.
 * SLA thresholds, model settings, and evaluation configuration.
 */
export default {
  thresholds: {
    contextRelevance: 0.80,
    faithfulness: 0.85,       // CI gate default
    answerRelevance: 0.80,
    hallucinationRate: 0.05,  // Max 5% hallucination
    recallAtK: 0.70,          // RMM-1 minimum
    latencyP95: 4000,         // ms
    ttftP90: 2000,            // ms
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
