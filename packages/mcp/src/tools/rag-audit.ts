import { z } from "zod";

export const ragAuditSchema = z.object({
  golden_set_path: z.string().optional().describe("Path to golden set JSON file"),
  metrics: z
    .array(z.string())
    .optional()
    .describe("Specific metrics to evaluate (default: all)"),
});

export type RagAuditInput = z.infer<typeof ragAuditSchema>;

export async function handleRagAudit(input: RagAuditInput): Promise<string> {
  return JSON.stringify({
    status: "not_implemented",
    message: "RAG audit tool is not yet implemented. Coming in Phase 1.",
    input,
  });
}
