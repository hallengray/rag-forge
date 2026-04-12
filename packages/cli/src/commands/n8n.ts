import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface N8nExportResult {
  success: boolean;
  output_path: string;
  nodes: number;
  error?: string;
}

export function registerN8nCommand(program: Command): void {
  program
    .command("n8n")
    .option(
      "-o, --output <file>",
      "Output file path",
      "n8n-workflow.json",
    )
    .option(
      "--mcp-url <url>",
      "MCP server SSE endpoint",
      "http://localhost:3100/sse",
    )
    .description("Export pipeline configuration as an importable n8n workflow")
    .action(async (options: { output: string; mcpUrl: string }) => {
      const spinner = ora("Generating n8n workflow...").start();

      try {
        const args = [
          "n8n-export",
          "--output",
          options.output,
          "--mcp-url",
          options.mcpUrl,
        ];

        const result = await runPythonModule({
          module: "rag_forge_core.cli",
          args,
        });

        if (result.exitCode !== 0) {
          spinner.fail("n8n export failed");
          logger.error(result.stderr || "Unknown error");
          process.exit(1);
        }

        const output: N8nExportResult = JSON.parse(
          result.stdout,
        ) as N8nExportResult;

        if (!output.success) {
          spinner.fail("n8n export failed");
          logger.error(output.error ?? "Unknown error");
          process.exit(1);
        }

        spinner.succeed(
          `Exported n8n workflow with ${String(output.nodes)} nodes`,
        );
        logger.info(`  Output: ${output.output_path}`);
        logger.info("");
        logger.info("Import this file into n8n via:");
        logger.info("  1. Open n8n dashboard");
        logger.info("  2. Click 'Import from File'");
        logger.info(`  3. Select ${output.output_path}`);
      } catch (error) {
        spinner.fail("n8n export failed");
        const message =
          error instanceof Error ? error.message : "Unknown error";
        logger.error(message);
        process.exit(1);
      }
    });
}
