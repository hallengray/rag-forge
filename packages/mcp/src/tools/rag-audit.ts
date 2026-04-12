import { z } from "zod";
import { runPythonModule } from "@rag-forge/shared";

export const ragAuditSchema = z.object({
  golden_set_path: z.string().optional().describe("Path to golden set JSON file"),
  metrics: z
    .array(z.string())
    .optional()
    .describe("Specific metrics to evaluate (default: all)"),
});

export type RagAuditInput = z.infer<typeof ragAuditSchema>;

export async function handleRagAudit(input: RagAuditInput): Promise<string> {
  const args = ["audit", "--judge", "mock"];

  if (input.golden_set_path) {
    args.push("--golden-set", input.golden_set_path);
  }

  const result = await runPythonModule({
    module: "rag_forge_evaluator.cli",
    args,
  });

  if (result.exitCode !== 0) {
    return result.stdout || JSON.stringify({
      status: "error",
      message: result.stderr || "Audit failed",
    });
  }

  return result.stdout;
}
