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

function getPackageRoot(): string {
  const currentDir = dirname(fileURLToPath(import.meta.url));
  // Works for both src/commands/*.ts (dev) and dist/*.js (production)
  // In dev: packages/cli/src/commands -> up 2 = packages/cli
  // In prod: packages/cli/dist -> up 1 = packages/cli
  // Use path segment check: if currentDir ends with "commands", we're in src/commands
  if (currentDir.endsWith("commands") || currentDir.endsWith("commands\\") || currentDir.endsWith("commands/")) {
    return resolve(currentDir, "..", "..");
  }
  return resolve(currentDir, "..");
}

function getManifestPath(): string {
  return resolve(getPackageRoot(), "src", "modules", "manifest.json");
}

function getTemplateSourceDir(): string {
  // Monorepo templates: packages/cli -> up 2 = monorepo root -> templates/
  return resolve(getPackageRoot(), "..", "..", "templates", "enterprise", "project", "src");
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
      let missingSources = 0;

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
          missingSources++;
          continue;
        }

        await mkdir(dirname(destPath), { recursive: true });
        await cp(srcPath, destPath);
        logger.success(`  Added: ${file.dest}`);
        added++;
      }

      logger.info(
        `\nAdded ${String(added)} files, skipped ${String(skipped)}, missing ${String(missingSources)}`,
      );

      // Fail if nothing was added due to missing sources — indicates packaging/manifest defect
      if (added === 0 && missingSources > 0) {
        logger.error(
          "No files were added because all sources are missing. This indicates a packaging or manifest problem.",
        );
        process.exit(1);
      }

      if (mod.dependencies.length > 0) {
        logger.info("\nInstall dependencies:");
        logger.info(`  pip install ${mod.dependencies.join(" ")}`);
      }
    });
}
