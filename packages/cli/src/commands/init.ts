import type { Command } from "commander";
import { logger } from "../lib/logger.js";
import type { TemplateType } from "../types/index.js";

const AVAILABLE_TEMPLATES: TemplateType[] = ["basic", "hybrid", "agentic", "enterprise", "n8n"];

export function registerInitCommand(program: Command): void {
  program
    .command("init")
    .argument("[template]", "Project template to use", "basic")
    .option("-d, --directory <dir>", "Target directory", ".")
    .option("--no-install", "Skip dependency installation")
    .description("Scaffold a new RAG project from a template")
    .action(async (template: string, options: { directory: string; install: boolean }) => {
      const templateName = template as TemplateType;

      if (!AVAILABLE_TEMPLATES.includes(templateName)) {
        logger.error(
          `Unknown template "${template}". Available: ${AVAILABLE_TEMPLATES.join(", ")}`,
        );
        process.exit(1);
      }

      logger.info(`Scaffolding ${templateName} RAG project in ${options.directory}...`);
      logger.warn("Template scaffolding is not yet implemented. Coming in Phase 1.");
    });
}
