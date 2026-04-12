import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface ReportResult {
  success: boolean;
  report_path?: string;
  chunk_count?: number;
  has_audit?: boolean;
  drift_baseline?: boolean;
  error?: string;
}

export function registerReportCommand(program: Command): void {
  program
    .command("report")
    .option("-o, --output <dir>", "Output directory for reports", "./reports")
    .option("--collection <name>", "Collection name", "rag-forge")
    .description("Generate a pipeline health report dashboard")
    .action(
      async (options: { output: string; collection: string }) => {
        const spinner = ora("Generating health report...").start();

        try {
          const result = await runPythonModule({
            module: "rag_forge_evaluator.cli",
            args: [
              "report",
              "--output",
              options.output,
              "--collection",
              options.collection,
            ],
          });

          if (result.exitCode !== 0) {
            let errorMessage = result.stderr || "Unknown error";
            try {
              const parsed = JSON.parse(result.stdout) as Partial<ReportResult>;
              if (parsed.error) errorMessage = parsed.error;
            } catch {
              // stdout is not JSON — use stderr
            }
            spinner.fail("Report generation failed");
            logger.error(errorMessage);
            process.exit(1);
          }

          const output: ReportResult = JSON.parse(result.stdout);

          if (!output.success) {
            spinner.fail("Report generation failed");
            logger.error(output.error ?? "Unknown error");
            process.exit(1);
          }

          spinner.succeed("Health report generated");
          logger.info(
            `Indexed chunks: ${String(output.chunk_count ?? 0)}`,
          );
          logger.info(
            `Audit data: ${output.has_audit ? "included" : "none available"}`,
          );
          logger.info(
            `Drift baseline: ${output.drift_baseline ? "configured" : "not configured"}`,
          );
          logger.success(`Report saved to: ${output.report_path ?? "unknown"}`);
        } catch (error) {
          spinner.fail("Report generation failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
