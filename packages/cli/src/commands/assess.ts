import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface AssessCriteria {
  level: number;
  name: string;
  passed: boolean;
  checks: { description: string; passed: boolean; source: string }[];
}

interface AssessResult {
  success: boolean;
  rmm_level: number;
  rmm_name: string;
  badge: string;
  criteria: AssessCriteria[];
  error?: string;
}

export function registerAssessCommand(program: Command): void {
  program
    .command("assess")
    .option("--config <json>", "Pipeline config as JSON string")
    .option("--audit-report <file>", "Path to latest audit JSON report")
    .option("-c, --collection <name>", "Collection name", "rag-forge")
    .description("Run RAG Maturity Model assessment")
    .action(
      async (options: {
        config?: string;
        auditReport?: string;
        collection: string;
      }) => {
        const spinner = ora("Running RMM assessment...").start();

        try {
          const args = ["assess"];
          if (options.config) {
            args.push("--config-json", options.config);
          }
          if (options.auditReport) {
            args.push("--audit-report", options.auditReport);
          }
          args.push("--collection", options.collection);

          const result = await runPythonModule({
            module: "rag_forge_evaluator.cli",
            args,
          });

          if (result.exitCode !== 0) {
            let errorMessage = result.stderr || "Unknown error";
            try {
              const parsed = JSON.parse(result.stdout) as Partial<AssessResult>;
              if (parsed.error) errorMessage = parsed.error;
            } catch {
              // stdout not JSON
            }
            spinner.fail("Assessment failed");
            logger.error(errorMessage);
            process.exit(1);
          }

          const output: AssessResult = JSON.parse(result.stdout);

          if (!output.success) {
            spinner.fail("Assessment failed");
            logger.error(output.error ?? "Unknown error");
            process.exit(1);
          }

          spinner.succeed(output.badge);

          for (const criteria of output.criteria) {
            const icon = criteria.passed ? "PASS" : "----";
            logger.info(`  [${icon}] RMM-${String(criteria.level)}: ${criteria.name}`);
            for (const check of criteria.checks) {
              const checkIcon = check.passed ? "+" : "-";
              const source = check.source !== "config" ? ` (${check.source})` : "";
              logger.info(`         [${checkIcon}] ${check.description}${source}`);
            }
          }
        } catch (error) {
          spinner.fail("Assessment failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
