export async function handleRagStatus(): Promise<string> {
  return JSON.stringify({
    status: "not_implemented",
    message: "RAG status tool is not yet implemented. Coming in Phase 1.",
    pipeline: {
      indexed: false,
      documentCount: 0,
      chunkCount: 0,
      cacheHitRate: null,
    },
  });
}
