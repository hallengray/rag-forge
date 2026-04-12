import { Command } from "commander";
import { registerInitCommand } from "./commands/init.js";
import { registerIndexCommand } from "./commands/index.js";
import { registerAuditCommand } from "./commands/audit.js";
import { registerQueryCommand } from "./commands/query.js";
import { registerServeCommand } from "./commands/serve.js";
import { registerDriftCommand } from "./commands/drift.js";
import { registerCostCommand } from "./commands/cost.js";
import { registerGoldenCommand } from "./commands/golden.js";

const program = new Command();

program
  .name("rag-forge")
  .description(
    "Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in",
  )
  .version("0.1.0");

registerInitCommand(program);
registerIndexCommand(program);
registerAuditCommand(program);
registerQueryCommand(program);
registerServeCommand(program);
registerDriftCommand(program);
registerCostCommand(program);
registerGoldenCommand(program);

program.parse();
