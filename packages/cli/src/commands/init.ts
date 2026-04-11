import { existsSync } from "node:fs";
import { cp, readFile, writeFile, readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Command } from "commander";
import { logger } from "../lib/logger.js";
import type { TemplateType } from "../types/index.js";

const AVAILABLE_TEMPLATES: TemplateType[] = ["basic", "hybrid", "agentic", "enterprise", "n8n"];

function getTemplatesDir(): string {
  const currentDir = dirname(fileURLToPath(import.meta.url));
  // dist/index.js lives at packages/cli/dist/
  // three levels up reaches the monorepo root where templates/ lives
  return resolve(currentDir, "..", "..", "..", "templates");
}

async function listFiles(dir: string, prefix = ""): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      files.push(...(await listFiles(join(dir, entry.name), rel)));
    } else {
      files.push(rel);
    }
  }
  return files;
}

export function registerInitCommand(program: Command): void {
  program
    .command("init")
    .argument("[template]", "Project template to use", "basic")
    .option("-d, --directory <dir>", "Target directory")
    .option("--no-install", "Skip dependency installation")
    .description("Scaffold a new RAG project from a template")
    .action(async (template: string, options: { directory?: string; install: boolean }) => {
      const templateName = template as TemplateType;

      if (!AVAILABLE_TEMPLATES.includes(templateName)) {
        logger.error(
          `Unknown template "${template}". Available: ${AVAILABLE_TEMPLATES.join(", ")}`,
        );
        process.exit(1);
      }

      const targetDir = resolve(options.directory ?? templateName);

      if (existsSync(targetDir) && options.directory !== ".") {
        const entries = await readdir(targetDir);
        if (entries.length > 0) {
          logger.error(`Directory "${targetDir}" already exists and is not empty.`);
          process.exit(1);
        }
      }

      const templatesDir = getTemplatesDir();
      const sourceDir = join(templatesDir, templateName, "project");

      if (!existsSync(sourceDir)) {
        logger.error(`Template "${templateName}" not found at ${sourceDir}`);
        process.exit(1);
      }

      logger.info(`Scaffolding ${templateName} RAG project in ${targetDir}...`);

      await cp(sourceDir, targetDir, { recursive: true });

      const projectName = targetDir.split(/[/\\]/).pop() ?? templateName;
      const pyprojectPath = join(targetDir, "pyproject.toml");
      if (existsSync(pyprojectPath)) {
        let content = await readFile(pyprojectPath, "utf-8");
        content = content.replace(/my-rag-pipeline/g, projectName);
        await writeFile(pyprojectPath, content, "utf-8");
      }

      const files = await listFiles(targetDir);
      for (const file of files) {
        logger.success(`  Created ${file}`);
      }

      logger.info("");
      logger.info("Next steps:");
      logger.info(`  cd ${targetDir}`);
      logger.info("  rag-forge index --source ./docs");
      logger.info("  rag-forge audit --golden-set eval/golden_set.json");
    });
}
