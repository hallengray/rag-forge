import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface GoldenAddResult {
  success: boolean;
  added: number;
  total: number;
  golden_set_path: string;
  source: string;
  error?: string;
}

interface GoldenValidateResult {
  success: boolean;
  valid: boolean;
  total_entries: number;
  errors: string[];
  error?: string;
}

export function registerGoldenCommand(program: Command): void {
  const golden = program
    .command("golden")
    .description("Golden set management for evaluation");

  golden
    .command("add")
    .requiredOption("-g, --golden-set <file>", "Path to golden set JSON", "eval/golden_set.json")
    .option("--from-traffic <file>", "Sample from telemetry JSONL file")
    .option("--sample-size <number>", "Number of entries to sample", "10")
    .option("--query <question>", "Question to add manually")
    .option("--keywords <list>", "Comma-separated expected keywords")
    .option("--difficulty <level>", "Difficulty: easy | medium | hard", "medium")
    .option("--topic <name>", "Topic category", "general")
    .description("Add entries to the golden set (manual or from traffic)")
    .action(
      async (options: {
        goldenSet: string;
        fromTraffic?: string;
        sampleSize: string;
        query?: string;
        keywords?: string;
        difficulty: string;
        topic: string;
      }) => {
        const spinner = ora("Adding to golden set...").start();

        try {
          const args = [
            "golden-add",
            "--golden-set",
            options.goldenSet,
          ];

          if (options.fromTraffic) {
            args.push("--from-traffic", options.fromTraffic);
            args.push("--sample-size", options.sampleSize);
          } else if (options.query && options.keywords) {
            args.push("--query", options.query);
            args.push("--keywords", options.keywords);
            args.push("--difficulty", options.difficulty);
            args.push("--topic", options.topic);
          } else {
            spinner.fail("Provide --from-traffic <file> or --query <q> --keywords <k>");
            process.exit(1);
          }

          const result = await runPythonModule({
            module: "rag_forge_evaluator.cli",
            args,
          });

          if (result.exitCode !== 0) {
            let errorMessage = result.stderr || "Unknown error";
            try {
              const parsed = JSON.parse(result.stdout) as Partial<GoldenAddResult>;
              if (parsed.error) errorMessage = parsed.error;
            } catch {
              // stdout is not JSON — use stderr
            }
            spinner.fail("Failed to add to golden set");
            logger.error(errorMessage);
            process.exit(1);
          }

          const output: GoldenAddResult = JSON.parse(result.stdout);

          if (output.success) {
            spinner.succeed(
              `Added ${String(output.added)} entries (total: ${String(output.total)}) → ${output.golden_set_path}`,
            );
          } else {
            spinner.fail("Failed to add to golden set");
            logger.error(output.error ?? "Unknown error");
            process.exit(1);
          }
        } catch (error) {
          spinner.fail("Failed to add to golden set");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );

  golden
    .command("validate")
    .requiredOption("-g, --golden-set <file>", "Path to golden set JSON", "eval/golden_set.json")
    .description("Validate golden set coverage, balance, and schema")
    .action(
      async (options: { goldenSet: string }) => {
        const spinner = ora("Validating golden set...").start();

        try {
          const result = await runPythonModule({
            module: "rag_forge_evaluator.cli",
            args: ["golden-validate", "--golden-set", options.goldenSet],
          });

          if (result.exitCode !== 0) {
            let errorMessage = result.stderr || "Unknown error";
            try {
              const parsed = JSON.parse(result.stdout) as Partial<GoldenValidateResult>;
              if (parsed.error) errorMessage = parsed.error;
            } catch {
              // stdout is not JSON — use stderr
            }
            spinner.fail("Validation failed");
            logger.error(errorMessage);
            process.exit(1);
          }

          const output: GoldenValidateResult = JSON.parse(result.stdout);

          if (output.valid) {
            spinner.succeed(
              `Golden set valid — ${String(output.total_entries)} entries, no issues`,
            );
          } else {
            spinner.warn(
              `Golden set has ${String(output.errors.length)} issue(s):`,
            );
            for (const err of output.errors) {
              logger.warn(`  - ${err}`);
            }
          }
        } catch (error) {
          spinner.fail("Validation failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
