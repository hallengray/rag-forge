# rag-forge-evaluator

RAG pipeline evaluation engine for the RAG-Forge toolkit: RAGAS, DeepEval, LLM-as-Judge, and the RAG Maturity Model.

## Installation

```bash
pip install rag-forge-evaluator
```

## Usage

```python
from rag_forge_evaluator.assess import RMMAssessor

assessor = RMMAssessor()
result = assessor.assess(config={
    "retrieval_strategy": "hybrid",
    "input_guard_configured": True,
    "output_guard_configured": True,
})
print(result.badge)  # e.g., "RMM-3 Better Trust"
```

## Features

- RMM (RAG Maturity Model) scoring (levels 0-5)
- RAGAS, DeepEval, and LLM-as-Judge evaluators
- Golden set management with traffic sampling
- Cost estimation
- HTML and PDF report generation

## License

MIT
