import { createServer as createHttpServer } from "node:http";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { createServer } from "../index.js";

export async function startHttpServer(port: number): Promise<void> {
  const mcpServer = createServer();
  let transport: SSEServerTransport | null = null;

  const httpServer = createHttpServer(async (req, res) => {
    if (req.method === "GET" && req.url === "/sse") {
      transport = new SSEServerTransport("/messages", res);
      await mcpServer.connect(transport);
    } else if (req.method === "POST" && req.url === "/messages") {
      if (transport === null) {
        res.writeHead(400);
        res.end("No active SSE connection");
        return;
      }
      await transport.handlePostMessage(req, res);
    } else if (req.method === "GET" && req.url === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", tools: 5 }));
    } else {
      res.writeHead(404);
      res.end("Not found");
    }
  });

  httpServer.listen(port, () => {
    console.error(`RAG-Forge MCP server listening on http://localhost:${String(port)}/sse`);
  });

  await new Promise<never>(() => {});
}
