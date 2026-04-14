# Changelog

## 0.2.0 — Evaluator Refresh (2026-04-14)

RAG-Forge's evaluator now understands what your RAG was built to do, and communicates its findings like an audit artifact.

### Breaking changes

- **Scores will shift for pipelines with safety refusals.** Refusal-aware scoring is default-on. Pipelines that correctly refuse to answer when the knowledge base lacks support will no longer be penalized as non-answers. Pass `--strict` to revert to v0.1.x scoring semantics.
- **The `ragas` optional extra now requires `ragas>=0.4,<0.6`.** If you pinned ragas 0.2.x elsewhere in your environment, upgrade to 0.4.x before upgrading `rag-forge-evaluator`.
- **`--evaluator ragas --judge claude` is now a supported combination.** It previously errored out with a ConfigurationError. If your CI relied on that error as a signal, update it accordingly.

### New

- **`RagForgeRagasLLM` and `RagForgeRagasEmbeddings` wrappers** — the RAGAS adapter now injects its own LLM and embeddings so it works across ragas major versions and honors `--judge` end-to-end.
- **`[ragas-voyage]` optional extra** — Claude-judge users can run RAGAS with Voyage embeddings via `pip install rag-forge-evaluator[ragas-voyage]`.
- **Refusal-aware scoring** — judge-driven inline classification + refusal rubric. Default-on; `--strict` escape hatch for the old semantics.
- **Top-tier audit report** — single template with shared browser/print stylesheet, historical sparkline, TL;DR callout, cost summary, safety-refusals section, and a compliance footer aligned with NIST AI RMF / ISO 42001 / EU AI Act Article 15.
- **CLI flags** — `--strict`, `--refusal-aware`, `--no-refusal-aware`.

### Fixed

- `OpenAIEmbeddings.embed_query` AttributeError on ragas 0.4.x (Finding #4 from Cycle 2).
- `gpt-4o-mini` max_tokens overflow on long structured clinical responses (Finding #5). The wrapper now honors `AuditConfig.ragas_max_tokens`, default 8192.
- RAGAS exceptions no longer silently coerce to score 0.0. Skipped samples are tracked as `SkipRecord`s and surfaced in both JSON and HTML/PDF reports (Finding #6).

### Migration guide

1. Run `pip install -U rag-forge-evaluator[ragas]` — ragas will upgrade to a supported version in the `>=0.4,<0.6` range automatically.
2. If you use Claude judge with ragas, also install Voyage embeddings: `pip install rag-forge-evaluator[ragas-voyage]`.
3. Re-run any baseline audits to establish new-scoring-mode baselines for your CI gates.
4. To preserve v0.1.x scoring semantics in CI, add `--strict` to your audit commands.

### Credits

This release is driven by findings from the Cycle 2 clinical audit (2026-04-14), which exercised RAG-Forge 0.1.3 against a real clinical RAG pipeline and exposed the three RAGAS bugs plus the safety-refusal scoring gap that v0.2.0 closes.
