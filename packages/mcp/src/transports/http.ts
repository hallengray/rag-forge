import { randomUUID } from "node:crypto";
import { createServer as createHttpServer } from "node:http";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { createServer } from "../index.js";

export async function startHttpServer(port: number): Promise<void> {
  const sessions = new Map<string, SSEServerTransport>();

  const httpServer = createHttpServer(async (req, res) => {
    const url = new URL(req.url ?? "/", `http://localhost:${String(port)}`);

    if (req.method === "GET" && url.pathname === "/sse") {
      const sessionId = randomUUID();
      const messagesPath = `/messages/${sessionId}`;
      const transport = new SSEServerTransport(messagesPath, res);
      sessions.set(sessionId, transport);

      // Clean up when the SSE connection closes
      res.on("close", () => {
        sessions.delete(sessionId);
      });

      // Each connection gets its own MCP server instance
      const mcpServer = createServer();
      await mcpServer.connect(transport);
    } else if (req.method === "POST" && url.pathname.startsWith("/messages/")) {
      const sessionId = url.pathname.replace("/messages/", "");
      const transport = sessions.get(sessionId);
      if (!transport) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Unknown session" }));
        return;
      }
      await transport.handlePostMessage(req, res);
    } else if (req.method === "GET" && url.pathname === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", sessions: sessions.size }));
    } else {
      res.writeHead(404);
      res.end("Not found");
    }
  });

  httpServer.listen(port, () => {
    console.error(`RAG-Forge MCP server listening on http://localhost:${String(port)}/sse`);
  });

  // eslint-disable-next-line @typescript-eslint/no-empty-function -- intentional: keep the process alive indefinitely
  await new Promise<never>(() => {});
}
