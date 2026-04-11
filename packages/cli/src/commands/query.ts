import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface QuerySource {
  text: string;
  score: number;
  id: string;
  source_document?: string;
}

interface QueryResult {
  answer: string;
  model_used: string;
  chunks_retrieved: number;
  sources: QuerySource[];
}

export function registerQueryCommand(program: Command): void {
  program
    .command("query")
    .argument("<question>", "The question to ask the RAG pipeline")
    .option("-k, --top-k <number>", "Number of chunks to retrieve", "5")
    .option("-e, --embedding <provider>", "Embedding provider: openai | local | mock", "mock")
    .option("-g, --generator <provider>", "Generation provider: claude | openai | mock", "mock")
    .option("-c, --collection <name>", "Collection name", "rag-forge")
    .option(
      "--strategy <type>",
      "Retrieval strategy: dense | sparse | hybrid",
      "dense",
    )
    .option(
      "--alpha <number>",
      "RRF alpha weighting for hybrid retrieval (0.0-1.0)",
      "0.6",
    )
    .option(
      "--reranker <type>",
      "Reranker: none | cohere | bge-local",
      "none",
    )
    .option(
      "--sparse-index-path <path>",
      "Path to BM25 sparse index",
    )
    .description("Execute a RAG query against the indexed pipeline")
    .action(
      async (
        question: string,
        options: {
          topK: string;
          embedding: string;
          generator: string;
          collection: string;
          strategy: string;
          alpha: string;
          reranker: string;
          sparseIndexPath?: string;
        },
      ) => {
        const spinner = ora("Querying pipeline...").start();

        try {
          const args = [
            "query",
            "--question",
            question,
            "--embedding",
            options.embedding,
            "--generator",
            options.generator,
            "--collection",
            options.collection,
            "--top-k",
            options.topK,
            "--strategy",
            options.strategy,
            "--alpha",
            options.alpha,
            "--reranker",
            options.reranker,
          ];

          if (options.sparseIndexPath) {
            args.push("--sparse-index-path", options.sparseIndexPath);
          }

          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args,
          });

          if (result.exitCode !== 0) {
            spinner.fail("Query failed");
            logger.error(result.stderr || "Unknown error");
            process.exit(1);
          }

          const output: QueryResult = JSON.parse(result.stdout);
          spinner.succeed(`Answer (${output.model_used}):`);

          console.log("");
          console.log(output.answer);
          console.log("");

          if (output.sources.length > 0) {
            logger.info(`Sources (${String(output.chunks_retrieved)} chunks):`);
            for (const source of output.sources) {
              logger.info(
                `  [${source.score.toFixed(3)}] ${source.text.slice(0, 120)}...`,
              );
            }
          }
        } catch (error) {
          spinner.fail("Query failed");
          const message = error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
