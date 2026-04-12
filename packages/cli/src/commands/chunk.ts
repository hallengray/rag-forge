import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface ChunkSample {
  index: number;
  source: string;
  preview: string;
}

interface ChunkStats {
  avg_chunk_size: number;
  min_chunk_size: number;
  max_chunk_size: number;
  total_tokens: number;
}

interface ChunkResult {
  success: boolean;
  strategy: string;
  chunk_size: number;
  total_chunks: number;
  stats: ChunkStats;
  samples: ChunkSample[];
  error?: string;
}

export function registerChunkCommand(program: Command): void {
  program
    .command("chunk")
    .option("-s, --source <directory>", "Source directory to chunk", "./docs")
    .option(
      "--strategy <type>",
      "Chunking strategy: fixed | recursive | semantic | structural | llm-driven",
      "recursive",
    )
    .option("--chunk-size <tokens>", "Target chunk size in tokens")
    .description("Preview chunking without indexing")
    .action(
      async (options: {
        source: string;
        strategy: string;
        chunkSize?: string;
      }) => {
        const spinner = ora("Chunking documents...").start();

        try {
          const args = [
            "chunk",
            "--source",
            options.source,
            "--strategy",
            options.strategy,
          ];

          if (options.chunkSize) {
            args.push("--chunk-size", options.chunkSize);
          }

          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args,
          });

          if (result.exitCode !== 0) {
            spinner.fail("Chunk preview failed");
            logger.error(result.stderr || "Unknown error");
            process.exit(1);
          }

          const output: ChunkResult = JSON.parse(
            result.stdout,
          ) as ChunkResult;

          if (!output.success) {
            spinner.fail("Chunk preview failed");
            logger.error(output.error ?? "Unknown error");
            process.exit(1);
          }

          spinner.succeed(
            `${String(output.total_chunks)} chunks (${output.strategy}, target ${String(output.chunk_size)} tokens)`,
          );

          console.log("");
          logger.info("Stats:");
          logger.info(
            `  Avg size: ${String(output.stats.avg_chunk_size)} tokens`,
          );
          logger.info(
            `  Min size: ${String(output.stats.min_chunk_size)} tokens`,
          );
          logger.info(
            `  Max size: ${String(output.stats.max_chunk_size)} tokens`,
          );
          logger.info(
            `  Total tokens: ${String(output.stats.total_tokens)}`,
          );

          if (output.samples.length > 0) {
            console.log("");
            logger.info("Sample chunks:");
            for (const sample of output.samples) {
              logger.info(
                `  [${String(sample.index)}] ${sample.source}: ${sample.preview}`,
              );
            }
          }
        } catch (error) {
          spinner.fail("Chunk preview failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
