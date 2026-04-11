import { describe, it, expect } from "vitest";
import { Command } from "commander";
import { registerInitCommand } from "../src/commands/init.js";
import { registerAuditCommand } from "../src/commands/audit.js";
import { registerQueryCommand } from "../src/commands/query.js";

describe("rag-forge CLI", () => {
  it("should register all commands without error", () => {
    const program = new Command();
    program.name("rag-forge").version("0.1.0");

    expect(() => registerInitCommand(program)).not.toThrow();
    expect(() => registerAuditCommand(program)).not.toThrow();
    expect(() => registerQueryCommand(program)).not.toThrow();
  });

  it("should have init, audit, and query commands", () => {
    const program = new Command();
    program.name("rag-forge").version("0.1.0");

    registerInitCommand(program);
    registerAuditCommand(program);
    registerQueryCommand(program);

    const commandNames = program.commands.map((cmd) => cmd.name());
    expect(commandNames).toContain("init");
    expect(commandNames).toContain("audit");
    expect(commandNames).toContain("query");
  });
});
