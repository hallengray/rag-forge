import { Command } from "commander";
import { registerInitCommand } from "./commands/init.js";
import { registerIndexCommand } from "./commands/index.js";
import { registerAuditCommand } from "./commands/audit.js";
import { registerQueryCommand } from "./commands/query.js";
import { registerServeCommand } from "./commands/serve.js";
import { registerDriftCommand } from "./commands/drift.js";
import { registerCostCommand } from "./commands/cost.js";
import { registerGoldenCommand } from "./commands/golden.js";
import { registerAssessCommand } from "./commands/assess.js";
import { registerGuardrailsCommand } from "./commands/guardrails.js";
import { registerReportCommand } from "./commands/report.js";
import { registerCacheCommand } from "./commands/cache.js";
import { registerInspectCommand } from "./commands/inspect.js";
import { registerAddCommand } from "./commands/add.js";
import { registerParseCommand } from "./commands/parse.js";
import { registerChunkCommand } from "./commands/chunk.js";
import { registerN8nCommand } from "./commands/n8n.js";

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
registerAssessCommand(program);
registerGuardrailsCommand(program);
registerReportCommand(program);
registerCacheCommand(program);
registerInspectCommand(program);
registerAddCommand(program);
registerParseCommand(program);
registerChunkCommand(program);
registerN8nCommand(program);

program.parse();
