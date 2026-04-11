import { describe, it, expect } from "vitest";
import { createServer } from "../src/index.js";

describe("RAG-Forge MCP Server", () => {
  it("should create a server instance without error", () => {
    const server = createServer();
    expect(server).toBeDefined();
  });
});
