import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface InspectResult {
  found: boolean;
  chunk_id: string;
  collection: string;
  text?: string;
  metadata?: Record<string, unknown>;
  error?: string;
}

export function registerInspectCommand(program: Command): void {
  program
    .command("inspect")
    .requiredOption("--chunk-id <id>", "The chunk ID to inspect")
    .option("--collection <name>", "Collection name", "rag-forge")
    .description("Inspect a specific chunk by ID")
    .action(
      async (options: { chunkId: string; collection: string }) => {
        const spinner = ora(
          `Inspecting chunk ${options.chunkId}...`,
        ).start();

        try {
          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args: [
              "inspect",
              "--chunk-id",
              options.chunkId,
              "--collection",
              options.collection,
            ],
          });

          if (result.exitCode !== 0) {
            spinner.fail("Inspection failed");
            logger.error(result.stderr || "Unknown error");
            process.exit(1);
          }

          const output: InspectResult = JSON.parse(result.stdout);

          if (!output.found) {
            spinner.warn(
              `Chunk not found: ${options.chunkId} in collection ${output.collection}`,
            );
            if (output.error) {
              logger.error(output.error);
            }
            return;
          }

          spinner.succeed(`Chunk found: ${output.chunk_id}`);
          logger.info(`Collection: ${output.collection}`);

          if (output.text !== undefined) {
            logger.info("Text:");
            logger.info(`  ${output.text}`);
          }

          if (output.metadata) {
            logger.info("Metadata:");
            for (const [key, value] of Object.entries(output.metadata)) {
              logger.info(`  ${key}: ${String(value)}`);
            }
          }
        } catch (error) {
          spinner.fail("Inspection failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
