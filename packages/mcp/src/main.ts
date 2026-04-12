import { startServer } from "./server.js";

startServer().catch((error: unknown) => {
  console.error("MCP server failed to start:", error);
  process.exit(1);
});
