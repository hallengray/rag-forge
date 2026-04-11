export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "scope-enum": [
      2,
      "always",
      ["cli", "core", "evaluator", "observability", "mcp", "templates", "ci", "docs"],
    ],
  },
};
