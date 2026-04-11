import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface IndexResult {
  success: boolean;
  documents_processed: number;
  chunks_created: number;
  chunks_indexed: number;
  errors: string[];
}

export function registerIndexCommand(program: Command): void {
  program
    .command("index")
    .requiredOption("-s, --source <dir>", "Source directory of documents to index")
    .option("-c, --collection <name>", "Collection name", "rag-forge")
    .option("-e, --embedding <provider>", "Embedding provider: openai | local | mock", "mock")
    .option("--strategy <name>", "Chunking strategy", "recursive")
    .description("Index documents into the vector store")
    .action(
      async (options: {
        source: string;
        collection: string;
        embedding: string;
        strategy: string;
      }) => {
        const spinner = ora("Indexing documents...").start();

        try {
          const configJson = JSON.stringify({
            embedding_provider: options.embedding,
            collection_name: options.collection,
            chunk_size: 512,
            overlap_ratio: 0.1,
          });

          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args: [
              "index",
              "--source",
              options.source,
              "--collection",
              options.collection,
              "--embedding",
              options.embedding,
              "--config-json",
              configJson,
            ],
          });

          if (result.exitCode !== 0) {
            spinner.fail("Indexing failed");
            logger.error(result.stderr || "Unknown error during indexing");
            process.exit(1);
          }

          const output: IndexResult = JSON.parse(result.stdout);

          if (output.success) {
            spinner.succeed("Indexing complete");
            logger.info(`Documents processed: ${String(output.documents_processed)}`);
            logger.info(`Chunks created: ${String(output.chunks_created)}`);
            logger.info(`Chunks indexed: ${String(output.chunks_indexed)}`);
          } else {
            spinner.warn("Indexing completed with errors");
            for (const error of output.errors) {
              logger.error(error);
            }
            process.exit(1);
          }
        } catch (error) {
          spinner.fail("Indexing failed");
          const message = error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
