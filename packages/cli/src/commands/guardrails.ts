import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface GuardrailsTestResult {
  success: boolean;
  total_tested: number;
  blocked: number;
  passed_through: number;
  pass_rate: number;
  by_category: Record<string, { tested: number; blocked: number; pass_rate: number }>;
  failures: { text: string; category: string; severity: string }[];
  error?: string;
}

interface PIIScanResult {
  success: boolean;
  chunks_scanned: number;
  chunks_with_pii: number;
  pii_types: Record<string, number>;
  affected_chunks: string[];
  error?: string;
}

export function registerGuardrailsCommand(program: Command): void {
  const guardrails = program
    .command("guardrails")
    .description("Security testing and PII scanning");

  guardrails
    .command("test")
    .option("--corpus <file>", "Path to custom adversarial corpus JSON")
    .description("Run adversarial prompt test suite against security guards")
    .action(
      async (options: { corpus?: string }) => {
        const spinner = ora("Running adversarial tests...").start();

        try {
          const args = ["guardrails-test"];
          if (options.corpus) {
            args.push("--corpus", options.corpus);
          }

          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args,
          });

          if (result.exitCode !== 0) {
            let errorMessage = result.stderr || "Unknown error";
            try {
              const parsed = JSON.parse(result.stdout) as Partial<GuardrailsTestResult>;
              if (parsed.error) errorMessage = parsed.error;
            } catch {
              // stdout not JSON
            }
            spinner.fail("Adversarial tests failed");
            logger.error(errorMessage);
            process.exit(1);
          }

          const output: GuardrailsTestResult = JSON.parse(result.stdout);

          if (!output.success) {
            spinner.fail("Adversarial tests failed");
            logger.error(output.error ?? "Unknown error");
            process.exit(1);
          }

          const passPercent = (output.pass_rate * 100).toFixed(1);
          if (output.failures.length === 0) {
            spinner.succeed(
              `All attacks blocked — ${String(output.blocked)}/${String(output.total_tested)} (${passPercent}% block rate)`,
            );
          } else {
            spinner.warn(
              `${String(output.failures.length)} attacks got through — ${String(output.blocked)}/${String(output.total_tested)} blocked (${passPercent}% block rate)`,
            );
          }

          logger.info("By category:");
          for (const [cat, stats] of Object.entries(output.by_category)) {
            const rate = (stats.pass_rate * 100).toFixed(0);
            logger.info(`  ${cat}: ${String(stats.blocked)}/${String(stats.tested)} blocked (${rate}%)`);
          }

          if (output.failures.length > 0) {
            logger.warn("Failures (attacks that got through):");
            for (const failure of output.failures) {
              logger.warn(`  [${failure.severity}] ${failure.category}: ${failure.text.slice(0, 80)}...`);
            }
          }
        } catch (error) {
          spinner.fail("Adversarial tests failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );

  guardrails
    .command("scan-pii")
    .option("-c, --collection <name>", "Collection name", "rag-forge")
    .description("Scan vector store for PII leakage")
    .action(
      async (options: { collection: string }) => {
        const spinner = ora("Scanning for PII...").start();

        try {
          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args: ["guardrails-scan-pii", "--collection", options.collection],
          });

          if (result.exitCode !== 0) {
            let errorMessage = result.stderr || "Unknown error";
            try {
              const parsed = JSON.parse(result.stdout) as Partial<PIIScanResult>;
              if (parsed.error) errorMessage = parsed.error;
            } catch {
              // stdout not JSON
            }
            spinner.fail("PII scan failed");
            logger.error(errorMessage);
            process.exit(1);
          }

          const output: PIIScanResult = JSON.parse(result.stdout);

          if (!output.success) {
            spinner.fail("PII scan failed");
            logger.error(output.error ?? "Unknown error");
            process.exit(1);
          }

          if (output.chunks_with_pii === 0) {
            spinner.succeed(
              `No PII found — ${String(output.chunks_scanned)} chunks scanned`,
            );
          } else {
            spinner.warn(
              `PII found in ${String(output.chunks_with_pii)}/${String(output.chunks_scanned)} chunks`,
            );
            logger.warn("PII types detected:");
            for (const [piiType, count] of Object.entries(output.pii_types)) {
              logger.warn(`  ${piiType}: ${String(count)} occurrences`);
            }
          }
        } catch (error) {
          spinner.fail("PII scan failed");
          const message =
            error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
