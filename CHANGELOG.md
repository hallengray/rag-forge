# Changelog

## 0.2.2 — Honest-Measurement Repair Release (unreleased)

Cycle 3 of the PearMedica clinical audit (2026-04-15) caught five gaps in v0.2.1. This release closes every one of them. No new features.

### Fixed

- **RAGAS engine crashed on every run** (Cycle 3 Finding C3-2, HIGH). `RagForgeRagasLLM` was shipped without the `.generate()` / `is_finished()` / `get_temperature()` / `set_run_config()` methods that ragas 0.4.x's `BaseRagasLLM` exposes. Every metric job crashed with `AttributeError: 'RagForgeRagasLLM' object has no attribute 'generate'` in roughly 6 seconds without making a single network call. v0.2.2 re-declares every public method on both `BaseRagasLLM` and `BaseRagasEmbeddings` as duck-typed shims, and a new contract test (`tests/test_ragas_adapters_contract.py`) iterates the real ragas base classes and asserts the wrappers match them — so the next ragas release that grows a new method fails fast in CI, not in a user audit.
- **Skipped counter silently wrong** (Cycle 3 residual of Cycle 2 Finding #6, MEDIUM). `EvaluationResult.skipped_evaluations` was never populated by the RAGAS engine, so the report's top-level "Skipped: N" line read `0` even when every job had crashed. Individual-metric extraction failures also produced one aggregate `SkipRecord` per metric name instead of fanning out per (sample, metric) pair — a 12-sample x 4-metric run produced 4 skip records instead of 48, under-reporting the blast radius by 12x. v0.2.2 fans out skips across every affected sample and keeps the integer counter in lockstep with the detail list. Reason strings are truncated to 400 chars with a trailing ellipsis so long Python tracebacks don't blow up HTML/PDF rendering.
- **`__version__` constant stale** (Cycle 3 Finding C3-5, LOW). `pip show rag-forge-evaluator` correctly reported `0.2.1` but `import rag_forge_evaluator; rag_forge_evaluator.__version__` returned `"0.1.0"`. Users programmatically tagging their audit reports with the tool version were recording wrong versions in their own records. v0.2.2 bumps the constant, adds the missing `__version__` to `rag_forge_observability`, and introduces `tests/test_version_drift.py` — a parametrized CI test that reads each package's `pyproject.toml` and `__init__.py` and asserts they stay in lockstep. Any future release bumping one half but forgetting the other fails in CI.

### Measurement rubric changes (read if upgrading from v0.1.x)

**Context Relevance scores are systematically higher under v0.2.x than v0.1.x — by ~0.25 on average against identical telemetry — and this is a rubric change, not product improvement.**

Cycle 3 observed every case in the 12-sample PearMedica golden set scoring higher on Context Relevance under v0.2.1's llm-judge than it did under v0.1.3's, with deltas from +0.05 to +0.48. The production retrieval code was unchanged between the two runs; only the measurement framework moved.

**Root cause (mechanistic):** v0.1.3 scored Context Relevance by **per-chunk averaging**. Its judge prompt (in `packages/evaluator/src/rag_forge_evaluator/metrics/context_relevance.py`) instructed the judge to rate each retrieved chunk individually on a 1-5 scale and return `mean_score = mean(ratings) / 5`:

```text
Rate each context chunk's relevance to the query on a 1-5 scale.
Respond with ... "ratings": [{"chunk_index": 0, "score": 4, ...}], "mean_score": 0.8}
The mean_score should be the average rating divided by 5 (normalized to 0.0-1.0).
```

v0.2.0's new combined llm_judge prompt (in `packages/evaluator/src/rag_forge_evaluator/metrics/llm_judge.py`, introduced in commit `330465f`) switched to a **holistic 0-1 score** across the whole context:

```text
- context_relevance (0-1): how relevant the retrieved context is to the query.
```

The two methodologies are not equivalent:

- Per-chunk averaging penalises the presence of irrelevant chunks. If 5 chunks are retrieved and 2 are relevant, the average is roughly `(5+5+1+1+1)/5/5 = 0.52`.
- Holistic scoring typically rewards the presence of at least some relevant information. Given the same 5 chunks, a judge will often return 0.80+ because "the context does contain relevant information."

Holistic scoring is systematically more lenient than averaged per-chunk scoring when retrieval surfaces a mix of relevant and irrelevant chunks — which is the normal case for hybrid retrieval pipelines. That is the mechanism behind the +0.25 drift.

**What this means for upgrading from v0.1.x:**

- **Do not read a Context Relevance jump as a product improvement** when upgrading. Your retrieval pipeline has not gotten better; the measurement got more lenient.
- **Re-baseline your CI gate thresholds after the first v0.2.x run** against a known-good pipeline. If your v0.1.x gate was `context_relevance >= 0.60`, you may need `>= 0.80` or higher under v0.2.x to catch the same drift magnitude.
- **The other three metrics** (faithfulness, answer_relevance, hallucination) also moved to the combined-pass prompt in v0.2.0, but their deltas against Cycle 2's telemetry were within LLM-judge variance (+0.02 to +0.06). Treat them as lightly noisy, not as rubric-changed, unless you see large per-case jumps.
- **Refusal-aware scoring is default-on in v0.2.0+** and adds a separate `safety_refusal` rubric with explicitly softer context-relevance criteria. That path only fires when the judge classifies a sample as a refusal; in the Cycle 3 run, 0 samples were classified as refusals, so the drift above is entirely on the `standard` rubric — not a side effect of refusal mode.

A future `--rubric=strict-v1` flag that pins the judge prompt to the v0.1.x per-chunk-averaging shape is under design for a later release. Not in v0.2.2. Open a GitHub issue if you need it before then.

### Verified fixed in this release

- **Cycle 2 Finding #4 (`OpenAIEmbeddings.embed_query` AttributeError):** contract test in `tests/test_ragas_adapters_contract.py` asserts `embed_query` + `aembed_query` + `embed_documents` + `aembed_documents` + `embed_text` + `embed_texts` + `set_run_config` are all declared on `RagForgeRagasEmbeddings`. End-to-end smoke test in `tests/test_ragas_adapters_e2e.py` runs `ragas.evaluate()` against the wrapper and asserts no `AttributeError` naming our classes.
- **Cycle 2 Finding #5 (`max_tokens` overflow on long structured clinical responses):** v0.2.0 raised `ClaudeJudge` default from 1024 -> 4096 tokens. `tests/test_cycle2_regression.py::test_cycle2_fixture_handles_long_structured_responses` asserts the absence of `InstructorRetryException` / `finish_reason='length'` signatures in skip records against a 3-sample long-response fixture.
- **Cycle 2 Finding #6 (silent 0.0 coercion):** two-part fix. v0.2.0 replaced the 0.0 fallback with `SkipRecord` tracking. v0.2.2 (this release) closes the residual gap where the `skipped_evaluations` integer counter was not kept in lockstep with the skip detail list — see Fixed above.

## 0.2.1 — Partial-Publish Recovery (2026-04-14)

Recovery release for a partial v0.2.0 publish. v0.2.0 shipped `rag-forge-core@0.2.0` and all three npm packages to registries, but `rag-forge-evaluator@0.2.0` and `rag-forge-observability@0.2.0` failed PyPI strict-ZIP validation with `400 Invalid distribution file. Duplicate filename in local headers` because `packages/evaluator/pyproject.toml` had a redundant `[tool.hatch.build.targets.wheel.force-include]` block that duplicated every template file inside the wheel archive.

### Fixed

- Removed the `force-include` block from `packages/evaluator/pyproject.toml` so wheels contain each template exactly once.
- Added `skip-existing: true` to all three `pypa/gh-action-pypi-publish` steps so partial-publish recoveries re-run cleanly without hard-failing on already-uploaded packages.
- Added a `verify` job that runs `twine check` + `check-wheel-contents` on every built Python wheel *before* any upload job starts. Structural wheel errors now fail at the verify step, not at the publish step.

All 6 packages now live at 0.2.1 on their respective registries.

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
