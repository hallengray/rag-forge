import { z } from "zod";

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
  return JSON.stringify({
    status: "not_implemented",
    message: "RAG query tool is not yet implemented. Coming in Phase 1.",
    input,
  });
}
