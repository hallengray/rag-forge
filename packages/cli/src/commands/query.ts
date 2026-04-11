import type { Command } from "commander";
import { logger } from "../lib/logger.js";

export function registerQueryCommand(program: Command): void {
  program
    .command("query")
    .argument("<question>", "The question to ask the RAG pipeline")
    .option("-k, --top-k <number>", "Number of chunks to retrieve", "5")
    .option("--agent-mode", "Enable multi-agent query decomposition")
    .description("Execute a RAG query against the indexed pipeline")
    .action(async (question: string, options: { topK: string; agentMode?: boolean }) => {
      logger.info(`Querying: "${question}" (top_k=${options.topK})`);
      logger.warn("Query engine is not yet implemented. Coming in Phase 1.");
    });
}
