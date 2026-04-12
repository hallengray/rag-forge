import { spawn } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Command } from "commander";
import { logger } from "../lib/logger.js";

function getMcpMainPath(): string {
  const currentDir = fileURLToPath(new URL(".", import.meta.url));
  return resolve(currentDir, "..", "..", "..", "mcp", "dist", "main.js");
}

export function registerServeCommand(program: Command): void {
  program
    .command("serve")
    .option("--mcp", "Launch MCP server on stdio")
    .description("Start the RAG-Forge server")
    .action(async (options: { mcp?: boolean }) => {
      if (!options.mcp) {
        logger.error("Please specify a server mode. Currently supported: --mcp");
        process.exit(1);
      }

      const mcpMain = getMcpMainPath();

      logger.info("Starting MCP server on stdio...");

      const child = spawn("node", [mcpMain], {
        stdio: "inherit",
      });

      child.on("error", (error) => {
        logger.error(`MCP server failed: ${error.message}`);
        process.exit(1);
      });

      child.on("exit", (code) => {
        process.exit(code ?? 0);
      });
    });
}
