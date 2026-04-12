import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
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
    .option("--mcp", "Launch MCP server")
    .option("--transport <type>", "Transport: stdio | http", "stdio")
    .option("-p, --port <number>", "Port for HTTP transport", "3100")
    .description("Start the RAG-Forge server")
    .action(async (options: { mcp?: boolean; transport: string; port: string }) => {
      if (!options.mcp) {
        logger.error("Please specify a server mode. Currently supported: --mcp");
        process.exit(1);
      }

      const mcpMain = getMcpMainPath();

      if (!existsSync(mcpMain)) {
        logger.error(`MCP server not found at ${mcpMain}. Run 'pnpm run build' first.`);
        process.exit(1);
      }

      const args = [mcpMain];
      if (options.transport === "http") {
        args.push("--transport", "http", "--port", options.port);
        logger.info(`Starting MCP server on http://localhost:${options.port}/sse`);
      } else {
        logger.info("Starting MCP server on stdio...");
      }

      const child = spawn(process.execPath, args, {
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
