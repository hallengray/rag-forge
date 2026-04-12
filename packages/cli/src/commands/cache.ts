import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface CacheStatsResult {
  success: boolean;
  hits?: number;
  misses?: number;
  total?: number;
  hit_rate?: number;
  source?: string;
  message?: string;
  error?: string;
}

export function registerCacheCommand(program: Command): void {
  const cache = program
    .command("cache")
    .description("Semantic cache management");

  cache
    .command("stats")
    .description("Show semantic cache hit/miss statistics")
    .action(async () => {
      const spinner = ora("Fetching cache statistics...").start();

      try {
        const result = await runPythonModule({
          module: "rag_forge_core.cli",
          args: ["cache-stats"],
        });

        if (result.exitCode !== 0) {
          let errorMessage = result.stderr || "Unknown error";
          try {
            const parsed = JSON.parse(
              result.stdout,
            ) as Partial<CacheStatsResult>;
            if (parsed.error) errorMessage = parsed.error;
          } catch {
            // stdout is not JSON — use stderr
          }
          spinner.fail("Failed to fetch cache stats");
          logger.error(errorMessage);
          process.exit(1);
        }

        const output: CacheStatsResult = JSON.parse(result.stdout);

        if (!output.success) {
          spinner.fail("Failed to fetch cache stats");
          logger.error(output.error ?? "Unknown error");
          process.exit(1);
        }

        spinner.succeed("Cache statistics");

        const hitRate = output.hit_rate ?? 0;
        const hitRatePercent = (hitRate * 100).toFixed(1);

        logger.info(`Hit rate:  ${hitRatePercent}%`);
        logger.info(`Hits:      ${String(output.hits ?? 0)}`);
        logger.info(`Misses:    ${String(output.misses ?? 0)}`);
        logger.info(`Total:     ${String(output.total ?? 0)}`);
        logger.info(`Source:    ${output.source ?? "unknown"}`);

        if (output.message) {
          logger.info(output.message);
        }
      } catch (error) {
        spinner.fail("Failed to fetch cache stats");
        const message =
          error instanceof Error ? error.message : "Unknown error";
        logger.error(message);
        process.exit(1);
      }
    });
}
