import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/python-bridge.ts"],
  format: ["esm"],
  target: "node20",
  dts: true,
  clean: true,
  sourcemap: true,
});
