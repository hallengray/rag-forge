import { startServer } from "./server.js";

const args = process.argv.slice(2);
const transportIdx = args.indexOf("--transport");
const transport = transportIdx >= 0 && args[transportIdx + 1] ? args[transportIdx + 1] : "stdio";
const portIdx = args.indexOf("--port");
const portArg = portIdx >= 0 ? args[portIdx + 1] : undefined;
const port = portArg !== undefined ? parseInt(portArg, 10) : 3100;

if (transport === "http" && (Number.isNaN(port) || port < 1 || port > 65535)) {
  console.error(`Invalid port: ${String(portArg ?? port)}. Must be 1-65535.`);
  process.exit(1);
}

async function main(): Promise<void> {
  if (transport === "http") {
    const { startHttpServer } = await import("./transports/http.js");
    await startHttpServer(port);
  } else {
    await startServer();
  }
}

main().catch((error: unknown) => {
  console.error("MCP server failed to start:", error);
  process.exit(1);
});
