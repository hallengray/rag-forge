# Evaluators

RAG-Forge ships with three evaluator engines:

- **`llm-judge`** — the default. A single judge model (Claude, OpenAI, or Mock) scores every sample on faithfulness, answer relevance, context relevance, and hallucination.
- **`ragas`** — integration with the [RAGAS](https://github.com/explodinggradients/ragas) framework.
- **`deepeval`** — integration with the [DeepEval](https://github.com/confident-ai/deepeval) framework.

Select an engine with `--evaluator llm-judge|ragas|deepeval`.

## Refusal-aware scoring (default-on in v0.2.0+)

When your RAG pipeline is built with a strict "don't fabricate" guardrail, traditional evaluators punish correct behavior. A pipeline that refuses to answer because the knowledge base lacks support scores low on answer-relevance and context-relevance — even though the refusal is exactly what the pipeline was designed to do.

RAG-Forge v0.2.0 fixes this with **refusal-aware scoring**. Before the judge scores a sample, it classifies the response as either `standard` or `safety_refusal`. Safety refusals are scored against a **refusal rubric** that rewards acknowledging the question and explaining why it cannot be answered, rather than penalizing the non-answer.

### Worked example — PearMedica Cycle 2

PearMedica's clinical RAG refused a parent's request for an exact paediatric metformin dose because the knowledge base contains adult dosing only. Under v0.1.3, this case scored 0.47 on answer relevance and 0.24 on context relevance — a safety win misclassified as a quality failure.

Under v0.2.0, the judge classifies it as `safety_refusal` with a justification like:

> *"Context lacks paediatric dosing; response correctly directs to clinical supervision without fabricating a dose."*

And the scores reflect the refusal rubric instead of the standard one.

### Default-on

Every audit in v0.2.0 runs with refusal-aware scoring unless you pass `--strict`. Your scores **will shift** if your pipeline has safety refusals — this is a correction, not a regression. The release notes call this out as a breaking change.

### Spot-check warning

If more than **30%** of your samples are classified as refusals, the report renders an amber banner asking you to audit the judge's classifications in the per-sample detail section. Always spot-check at least one sample per scoring mode on your first run — this mode trusts the judge's classification, and you need to verify it's classifying the way you expect.

### Escape hatch

Pass `--strict` (or `--no-refusal-aware`) to revert to v0.1.x semantics:

```bash
rag-forge-eval audit --input my-eval.jsonl --judge claude --strict
```

This disables the classification preamble entirely. Every sample is scored on the standard rubric, matching v0.1.x behavior.

### Works with both llm-judge and ragas

The classification preamble is injected into both evaluator paths:

- **`llm-judge`**: the full classification preamble + refusal rubric is added to the scoring prompt. The judge returns `scoring_mode` and `refusal_justification` alongside the metric scores in one response.
- **`ragas`**: a shorter NOTE is prepended to every prompt ragas sends to our `RagForgeRagasLLM` wrapper. Because ragas controls its own per-metric prompt templates, we cannot inject the full rubric — but the shorter note nudges ragas's judgments in the right direction for safety refusals.

If you write custom evaluators that subclass `EvaluatorInterface`, you'll need to opt-in to refusal-aware scoring manually. The default-on behavior applies only to the evaluators RAG-Forge ships.
