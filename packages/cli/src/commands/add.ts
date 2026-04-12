import { existsSync, readFileSync } from "node:fs";
import { cp, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Command } from "commander";
import { logger } from "../lib/logger.js";

interface ModuleFile {
  src: string;
  dest: string;
}

interface ModuleDefinition {
  description: string;
  files: ModuleFile[];
  dependencies: string[];
}

interface ModuleManifest {
  modules: Record<string, ModuleDefinition>;
}

function getManifestPath(): string {
  const currentDir = dirname(fileURLToPath(import.meta.url));
  // dist/index.js -> packages/cli/dist/ -> up to packages/cli/ -> src/modules/manifest.json
  return resolve(currentDir, "..", "src", "modules", "manifest.json");
}

function getTemplateSourceDir(): string {
  const currentDir = dirname(fileURLToPath(import.meta.url));
  // dist/index.js -> packages/cli/dist/ -> up three levels to monorepo root -> templates/
  return resolve(currentDir, "..", "..", "..", "templates", "enterprise", "project", "src");
}

export function registerAddCommand(program: Command): void {
  program
    .command("add")
    .argument(
      "<module>",
      "Module to add: guardrails | caching | reranking | enrichment | observability | hybrid-retrieval",
    )
    .description("Add a feature module as editable source code (shadcn/ui model)")
    .action(async (moduleName: string) => {
      const manifestPath = getManifestPath();
      if (!existsSync(manifestPath)) {
        logger.error(`Module manifest not found at ${manifestPath}`);
        process.exit(1);
      }

      const manifest: ModuleManifest = JSON.parse(
        readFileSync(manifestPath, "utf-8"),
      ) as ModuleManifest;
      const mod = manifest.modules[moduleName];

      if (!mod) {
        const available = Object.keys(manifest.modules).join(", ");
        logger.error(`Unknown module: ${moduleName}. Available: ${available}`);
        process.exit(1);
      }

      logger.info(`Adding module: ${moduleName} — ${mod.description}`);

      const sourceDir = getTemplateSourceDir();
      let added = 0;
      let skipped = 0;

      for (const file of mod.files) {
        const srcPath = resolve(sourceDir, file.src);
        const destPath = resolve(process.cwd(), file.dest);

        if (existsSync(destPath)) {
          logger.warn(`  Skip (exists): ${file.dest}`);
          skipped++;
          continue;
        }

        if (!existsSync(srcPath)) {
          logger.warn(`  Skip (source not found): ${file.src}`);
          skipped++;
          continue;
        }

        await mkdir(dirname(destPath), { recursive: true });
        await cp(srcPath, destPath);
        logger.success(`  Added: ${file.dest}`);
        added++;
      }

      logger.info(`\nAdded ${String(added)} files, skipped ${String(skipped)}`);

      if (mod.dependencies.length > 0) {
        logger.info("\nInstall dependencies:");
        logger.info(`  pip install ${mod.dependencies.join(" ")}`);
      }
    });
}
