import { execa } from "execa";
import { logger } from "./logger.js";

interface PythonBridgeOptions {
  module: string;
  args?: string[];
  cwd?: string;
}

interface PythonBridgeResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export async function runPythonModule(options: PythonBridgeOptions): Promise<PythonBridgeResult> {
  const { module, args = [], cwd } = options;

  logger.debug(`Running Python module: ${module} ${args.join(" ")}`);

  try {
    const result = await execa("uv", ["run", "python", "-m", module, ...args], {
      cwd,
      reject: false,
    });

    return {
      stdout: result.stdout,
      stderr: result.stderr,
      exitCode: result.exitCode ?? 0,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    logger.error(`Python bridge error: ${message}`);
    return {
      stdout: "",
      stderr: message,
      exitCode: 1,
    };
  }
}

export async function checkPythonAvailable(): Promise<boolean> {
  try {
    const result = await execa("uv", ["run", "python", "--version"], { reject: false });
    return result.exitCode === 0;
  } catch {
    return false;
  }
}
