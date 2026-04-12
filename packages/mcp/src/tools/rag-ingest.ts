import { z } from "zod";
import { runPythonModule } from "@rag-forge/shared";

export const ragIngestSchema = z.object({
  source_path: z.string().describe("Path to source directory of documents to index"),
  collection: z.string().default("rag-forge").describe("Collection name"),
  embedding: z.string().default("mock").describe("Embedding provider: openai | local | mock"),
  enrich: z.boolean().default(false).describe("Enable contextual enrichment"),
  sparse_index_path: z.string().optional().describe("Path to persist BM25 sparse index"),
});

export type RagIngestInput = z.infer<typeof ragIngestSchema>;

export async function handleRagIngest(input: RagIngestInput): Promise<string> {
  const args = ["index", "--source", input.source_path, "--collection", input.collection, "--embedding", input.embedding];
  if (input.enrich) args.push("--enrich");
  if (input.sparse_index_path) args.push("--sparse-index-path", input.sparse_index_path);

  const result = await runPythonModule({ module: "rag_forge_core.cli", args });
  if (result.exitCode !== 0) {
    return result.stdout || JSON.stringify({ status: "error", message: result.stderr || "Indexing failed" });
  }
  return result.stdout;
}
