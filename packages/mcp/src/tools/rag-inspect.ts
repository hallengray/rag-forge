import { z } from "zod";
import { runPythonModule } from "@rag-forge/shared";

export const ragInspectSchema = z.object({
  chunk_id: z.string().describe("The ID of the chunk to inspect"),
  collection: z.string().default("rag-forge").describe("Collection name"),
});

export type RagInspectInput = z.infer<typeof ragInspectSchema>;

export async function handleRagInspect(input: RagInspectInput): Promise<string> {
  const result = await runPythonModule({
    module: "rag_forge_core.cli",
    args: ["inspect", "--chunk-id", input.chunk_id, "--collection", input.collection],
  });
  if (result.exitCode !== 0) {
    return result.stdout || JSON.stringify({ status: "error", message: result.stderr || "Inspect failed" });
  }
  return result.stdout;
}
