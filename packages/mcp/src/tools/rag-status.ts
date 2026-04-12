import { runPythonModule } from "@rag-forge/shared";

export async function handleRagStatus(): Promise<string> {
  const result = await runPythonModule({
    module: "rag_forge_core.cli",
    args: ["status"],
  });

  if (result.exitCode !== 0) {
    return result.stdout || JSON.stringify({
      status: "error",
      message: result.stderr || "Failed to get pipeline status",
    });
  }

  return result.stdout;
}
