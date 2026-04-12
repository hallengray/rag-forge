import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface DriftResult {
  success: boolean;
  is_drifting?: boolean;
  distance?: number;
  threshold?: number;
  details?: string;
  error?: string;
  baseline_path?: string;
  vectors_saved?: number;
}

export function registerDriftCommand(program: Command): void {
  const drift = program
    .command("drift")
    .description("Query drift detection and baseline management");

  drift
    .command("report")
    .requiredOption("--current <file>", "Path to current embeddings JSON")
    .requiredOption("--baseline <file>", "Path to baseline embeddings JSON")
    .option("--threshold <number>", "Drift threshold (cosine distance)", "0.15")
    .description("Analyze query distribution drift from baseline")
    .action(
      async (options: {
        current: string;
        baseline: string;
        threshold: string;
      }) => {
        const spinner = ora("Analyzing query drift...").start();

        try {
          const result = await runPythonModule({
            module: "rag_forge_observability.cli",
            args: [
              "drift-report",
              "--current",
              options.current,
              "--baseline",
              options.baseline,
              "--threshold",
              options.threshold,
            ],
          });

          if (result.exitCode !== 0) {
            spinner.fail("Drift analysis failed");
            logger.error(result.stderr || "Unknown error");
            process.exit(1);
          }

          const output: DriftResult = JSON.parse(result.stdout);

          if (!output.success) {
            spinner.fail("Drift analysis failed");
            logger.error(output.error ?? "Unknown error");
            process.exit(1);
          }

          if (output.is_drifting) {
            spinner.warn(
              `DRIFT DETECTED — distance: ${output.distance?.toFixed(4)} (threshold: ${output.threshold?.toFixed(4)})`,
            );
          } else {
            spinner.succeed(
              `No drift — distance: ${output.distance?.toFixed(4)} (threshold: ${output.threshold?.toFixed(4)})`,
            );
          }

          if (output.details) {
            logger.info(output.details);
          }
        } catch (error) {
          spinner.fail("Drift analysis failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );

  drift
    .command("save-baseline")
    .requiredOption("--embeddings <file>", "Path to embeddings JSON")
    .requiredOption("--output <file>", "Path to save baseline")
    .description("Save current embeddings as drift baseline")
    .action(async (options: { embeddings: string; output: string }) => {
      const spinner = ora("Saving drift baseline...").start();

      try {
        const result = await runPythonModule({
          module: "rag_forge_observability.cli",
          args: [
            "drift-save-baseline",
            "--embeddings",
            options.embeddings,
            "--output",
            options.output,
          ],
        });

        if (result.exitCode !== 0) {
          spinner.fail("Failed to save baseline");
          logger.error(result.stderr || "Unknown error");
          process.exit(1);
        }

        const output: DriftResult = JSON.parse(result.stdout);

        if (output.success) {
          spinner.succeed(
            `Baseline saved: ${String(output.vectors_saved)} vectors → ${output.baseline_path}`,
          );
        } else {
          spinner.fail("Failed to save baseline");
          logger.error(output.error ?? "Unknown error");
          process.exit(1);
        }
      } catch (error) {
        spinner.fail("Failed to save baseline");
        const message =
          error instanceof Error ? error.message : "Unknown error";
        logger.error(message);
        process.exit(1);
      }
    });
}
