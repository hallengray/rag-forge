import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { logger } from "../lib/logger.js";

interface FileInfo {
  path: string;
  characters: number;
}

interface ParseResult {
  success: boolean;
  files_found: number;
  files: FileInfo[];
  total_characters: number;
  parse_errors: string[];
  error?: string;
}

export function registerParseCommand(program: Command): void {
  program
    .command("parse")
    .option("-s, --source <directory>", "Source directory to parse", "./docs")
    .description("Preview document extraction without indexing")
    .action(async (options: { source: string }) => {
      const spinner = ora("Parsing documents...").start();

      try {
        const args = ["parse", "--source", options.source];

        const result = await runPythonModule({
          module: "rag_forge_core.cli",
          args,
        });

        if (result.exitCode !== 0) {
          let errorMessage = result.stderr || "Unknown error";
          try {
            const parsed = JSON.parse(result.stdout) as Partial<ParseResult>;
            if (parsed.error) errorMessage = parsed.error;
          } catch {
            // stdout not JSON
          }
          spinner.fail("Parse preview failed");
          logger.error(errorMessage);
          process.exit(1);
        }

        const output: ParseResult = JSON.parse(result.stdout) as ParseResult;

        if (!output.success) {
          spinner.fail("Parse preview failed");
          logger.error(output.error ?? "Unknown error");
          process.exit(1);
        }

        spinner.succeed(
          `Found ${String(output.files_found)} files (${String(output.total_characters)} characters)`,
        );

        if (output.files.length > 0) {
          console.log("");
          for (const file of output.files) {
            logger.info(`  ${file.path} (${String(file.characters)} chars)`);
          }
        }

        if (output.parse_errors.length > 0) {
          console.log("");
          logger.warn(`${String(output.parse_errors.length)} parse errors:`);
          for (const err of output.parse_errors) {
            logger.warn(`  ${err}`);
          }
        }
      } catch (error) {
        spinner.fail("Parse preview failed");
        const message =
          error instanceof Error ? error.message : "Unknown error";
        logger.error(message);
        process.exit(1);
      }
    });
}
