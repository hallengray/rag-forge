import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface CostBreakdown {
  model: string;
  input_tokens_per_query: number;
  output_tokens_per_query: number;
  cost_per_query: number;
}

interface CostResult {
  success: boolean;
  daily_cost: number;
  monthly_cost: number;
  queries_per_day: number;
  breakdown: CostBreakdown[];
  error?: string;
}

export function registerCostCommand(program: Command): void {
  program
    .command("cost")
    .requiredOption("--telemetry <file>", "Path to telemetry JSON file")
    .option(
      "--queries-per-day <number>",
      "Projected daily query volume (overrides telemetry file)",
    )
    .description("Estimate monthly pipeline costs from telemetry")
    .action(
      async (options: {
        telemetry: string;
        queriesPerDay?: string;
      }) => {
        const spinner = ora("Estimating costs...").start();

        try {
          const args = ["cost", "--telemetry", options.telemetry];
          if (options.queriesPerDay) {
            args.push("--queries-per-day", options.queriesPerDay);
          }

          const result = await runPythonModule({
            module: "rag_forge_evaluator.cli",
            args,
          });

          if (result.exitCode !== 0) {
            let errorMessage = result.stderr || "Unknown error";
            try {
              const parsed = JSON.parse(result.stdout) as Partial<CostResult>;
              if (parsed.error) errorMessage = parsed.error;
            } catch {
              // stdout is not JSON — use stderr
            }
            spinner.fail("Cost estimation failed");
            logger.error(errorMessage);
            process.exit(1);
          }

          const output: CostResult = JSON.parse(result.stdout);

          if (!output.success) {
            spinner.fail("Cost estimation failed");
            logger.error(output.error ?? "Unknown error");
            process.exit(1);
          }

          spinner.succeed("Cost estimation complete");
          logger.info(
            `Daily cost:   $${output.daily_cost.toFixed(4)} (${String(output.queries_per_day)} queries/day)`,
          );
          logger.info(`Monthly cost: $${output.monthly_cost.toFixed(2)}`);

          if (output.breakdown.length > 0) {
            logger.info("Breakdown by model:");
            for (const item of output.breakdown) {
              logger.info(
                `  ${item.model}: $${item.cost_per_query.toFixed(6)}/query`,
              );
            }
          }
        } catch (error) {
          spinner.fail("Cost estimation failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
