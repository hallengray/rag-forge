# My RAG Pipeline

Scaffolded by [RAG-Forge](https://github.com/hallengray/rag-forge) using the `basic` template.

## Quick Start

```bash
# Install dependencies
uv sync

# Index your documents
rag-forge index --source ./docs

# Query the pipeline
rag-forge query "What is...?"

# Run evaluation
rag-forge audit --golden-set eval/golden_set.json

# Check maturity level
rag-forge assess
```

## Structure

- `src/pipeline.py` — Main RAG pipeline (customize this)
- `src/config.py` — Pipeline configuration
- `eval/golden_set.json` — Evaluation dataset (add your Q&A pairs)
- `eval/config.yaml` — Evaluation thresholds and CI gate settings
