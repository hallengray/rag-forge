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

## Bring your own judge provider

`rag-forge-evaluator` ships with Claude and OpenAI judges out of the box, but the `JudgeProvider` protocol is intentionally minimal so you can plug in any LLM — Gemini, Cohere, Bedrock, Ollama, vLLM, or a private model behind your own gateway. Implementing one is ~20 lines:

```python
# my_gemini_judge.py
import os
import google.generativeai as genai


class GeminiJudge:
    """Minimal judge implementation backed by Google Gemini."""

    def __init__(self, model: str = "gemini-2.5-pro", api_key: str | None = None) -> None:
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=key)
        self._model_name = model
        self._client = genai.GenerativeModel(model)

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.generate_content(
            [system_prompt, user_prompt],
            generation_config={"max_output_tokens": 4096},
        )
        return response.text or ""

    def model_name(self) -> str:
        return self._model_name
```

Wire it into an audit by passing the instance directly to `LLMJudgeEvaluator`:

```python
from my_gemini_judge import GeminiJudge
from rag_forge_evaluator.metrics.llm_judge import LLMJudgeEvaluator

judge = GeminiJudge(model="gemini-2.5-pro")
evaluator = LLMJudgeEvaluator(judge=judge)
result = evaluator.evaluate(samples)
```

The protocol contract:

```python
class JudgeProvider(Protocol):
    def judge(self, system_prompt: str, user_prompt: str) -> str: ...
    def model_name(self) -> str: ...
```

That's it. Anything that responds to those two methods works. Implementation hints:

- **Always set `max_tokens` >= 4096** for faithfulness/hallucination metrics. Long responses produce 30-50 enumerated claims; smaller budgets truncate the JSON mid-array and the metric ends up `skipped`.
- **Wrap your client with retry logic** for transient 429/5xx. The Anthropic and OpenAI SDKs honor a `max_retries` constructor arg with built-in exponential backoff — most provider SDKs offer something similar.
- **Return the raw response text**, including any prose around the JSON. The shared response parser handles code fences, leading prose, trailing prose, and truncated output, so you don't need to clean anything up.

First-party Gemini, Bedrock, and Ollama judges are tracked for v0.1.2.

## License

MIT
