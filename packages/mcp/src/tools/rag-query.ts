import { z } from "zod";
import { runPythonModule } from "@rag-forge/shared";

export const ragQuerySchema = z.object({
  query: z.string().describe("The question to ask the RAG pipeline"),
  top_k: z.number().int().min(1).max(100).default(5).describe("Number of chunks to retrieve"),
  agent_mode: z
    .boolean()
    .default(false)
    .describe("Enable multi-agent query decomposition for complex queries"),
});

export type RagQueryInput = z.infer<typeof ragQuerySchema>;

export async function handleRagQuery(input: RagQueryInput): Promise<string> {
  const result = await runPythonModule({
    module: "rag_forge_core.cli",
    args: [
      "query",
      "--question", input.query,
      "--top-k", String(input.top_k),
      "--embedding", "mock",
      "--generator", "mock",
      "--strategy", "dense",
    ],
  });

  if (result.exitCode !== 0) {
    return result.stdout || JSON.stringify({
      status: "error",
      message: result.stderr || "Query failed",
    });
  }

  return result.stdout;
}
