import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { ragQuerySchema, handleRagQuery } from "./tools/rag-query.js";
import { ragAuditSchema, handleRagAudit } from "./tools/rag-audit.js";
import { handleRagStatus } from "./tools/rag-status.js";

export function createServer(): McpServer {
  const server = new McpServer({
    name: "rag-forge",
    version: "0.1.0",
  });

  server.tool("rag_query", "Execute a RAG query against the indexed pipeline", ragQuerySchema.shape, async (input) => {
    const result = await handleRagQuery(ragQuerySchema.parse(input));
    return { content: [{ type: "text" as const, text: result }] };
  });

  server.tool("rag_audit", "Run evaluation suite and return results", ragAuditSchema.shape, async (input) => {
    const result = await handleRagAudit(ragAuditSchema.parse(input));
    return { content: [{ type: "text" as const, text: result }] };
  });

  server.tool("rag_status", "Return pipeline health metrics and cache stats", {}, async () => {
    const result = await handleRagStatus();
    return { content: [{ type: "text" as const, text: result }] };
  });

  return server;
}
