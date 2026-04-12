import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface AuditMetric {
  name: string;
  score: number;
  threshold: number;
  passed: boolean;
}

interface AuditResult {
  success: boolean;
  overall_score: number;
  passed: boolean;
  rmm_level: number;
  rmm_name: string;
  samples_evaluated: number;
  metrics: AuditMetric[];
  report_path: string;
  json_report_path: string;
  evaluator_engine: string;
  pdf_report_path: string | null;
}

export function registerAuditCommand(program: Command): void {
  program
    .command("audit")
    .option("-i, --input <file>", "Path to telemetry JSONL file")
    .option("-g, --golden-set <file>", "Path to golden set JSON file")
    .option("-j, --judge <model>", "Judge model: mock | claude | openai", "mock")
    .option("-o, --output <dir>", "Output directory for reports", "./reports")
    .option("--evaluator <engine>", "Evaluator engine: llm-judge | ragas | deepeval", "llm-judge")
    .option("--pdf", "Generate PDF report (requires Playwright)")
    .description("Run evaluation on pipeline telemetry and generate audit report")
    .action(
      async (options: {
        input?: string;
        goldenSet?: string;
        judge: string;
        output: string;
        evaluator: string;
        pdf?: boolean;
      }) => {
        if (!options.input && !options.goldenSet) {
          logger.error("Either --input or --golden-set is required");
          process.exit(1);
        }

        const spinner = ora("Running RAG pipeline audit...").start();

        try {
          const args = ["audit", "--judge", options.judge, "--output", options.output, "--evaluator", options.evaluator];

          if (options.input) {
            args.push("--input", options.input);
          }
          if (options.goldenSet) {
            args.push("--golden-set", options.goldenSet);
          }
          if (options.pdf) {
            args.push("--pdf");
          }

          const result = await runPythonModule({
            module: "rag_forge_evaluator.cli",
            args,
          });

          if (result.exitCode !== 0) {
            spinner.fail("Audit failed");
            logger.error(result.stderr || "Unknown error during audit");
            process.exit(1);
          }

          const output: AuditResult = JSON.parse(result.stdout);

          if (output.passed) {
            spinner.succeed(
              `Audit passed — RMM-${String(output.rmm_level)}: ${output.rmm_name}`,
            );
          } else {
            spinner.warn(
              `Audit completed — RMM-${String(output.rmm_level)}: ${output.rmm_name}`,
            );
          }

          logger.info(`Overall score: ${output.overall_score.toFixed(2)}`);
          logger.info(`Samples evaluated: ${String(output.samples_evaluated)}`);

          for (const metric of output.metrics) {
            const status = metric.passed ? "PASS" : "FAIL";
            logger.info(
              `  ${metric.name}: ${metric.score.toFixed(2)} (threshold: ${metric.threshold.toFixed(2)}) [${status}]`,
            );
          }

          logger.info(`Evaluator: ${output.evaluator_engine}`);
          logger.success(`Report saved to: ${output.report_path}`);
          if (output.pdf_report_path) {
            logger.success(`PDF report: ${output.pdf_report_path}`);
          }
        } catch (error) {
          spinner.fail("Audit failed");
          const message = error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
