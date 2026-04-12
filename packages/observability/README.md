# rag-forge-observability

OpenTelemetry tracing and query drift detection for the RAG-Forge toolkit.

## Installation

```bash
pip install rag-forge-observability
```

## Usage

```python
from rag_forge_observability.drift import DriftDetector, DriftBaseline

baseline = DriftBaseline(embeddings=[[1.0, 0.0, 0.0]])
detector = DriftDetector(threshold=0.15)
report = detector.analyze(current_embeddings=[[0.9, 0.1, 0.0]], baseline=baseline)
print(f"Drift detected: {report.is_drifting}")
```

## Features

- OpenTelemetry tracing for all RAG pipeline stages
- Query drift detection with baseline comparison
- Centroid-based cosine distance analysis

## License

MIT
