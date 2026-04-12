"""Plugin registry for custom chunkers, retrievers, and metrics.

Plugins can register via:
1. Direct API: registry.register_chunker("my-strategy", MyChunker)
2. Entry points: [project.entry-points."rag_forge.chunkers"]
   my-strategy = "my_package:MyChunker"

The chunker factory falls back to the registry when it encounters
an unknown strategy name.
"""

import importlib.metadata
import logging

_LOG = logging.getLogger(__name__)

_global_registry: "PluginRegistry | None" = None


class PluginRegistry:
    """Registry for custom RAG-Forge plugins.

    Supports three extension points:
    - chunkers: Custom chunking strategies (must implement ChunkStrategy ABC)
    - retrievers: Custom retrieval strategies (must implement RetrieverProtocol)
    - metrics: Custom evaluation metrics (must implement MetricEvaluator protocol)
    """

    def __init__(self) -> None:
        self._chunkers: dict[str, type] = {}
        self._retrievers: dict[str, type] = {}
        self._metrics: dict[str, type] = {}

    # --- Chunkers ---

    def register_chunker(self, name: str, cls: type) -> None:
        self._chunkers[name] = cls

    def get_chunker(self, name: str) -> type | None:
        return self._chunkers.get(name)

    def list_chunkers(self) -> list[str]:
        return list(self._chunkers.keys())

    # --- Retrievers ---

    def register_retriever(self, name: str, cls: type) -> None:
        self._retrievers[name] = cls

    def get_retriever(self, name: str) -> type | None:
        return self._retrievers.get(name)

    def list_retrievers(self) -> list[str]:
        return list(self._retrievers.keys())

    # --- Metrics ---

    def register_metric(self, name: str, cls: type) -> None:
        self._metrics[name] = cls

    def get_metric(self, name: str) -> type | None:
        return self._metrics.get(name)

    def list_metrics(self) -> list[str]:
        return list(self._metrics.keys())

    # --- Entry Point Discovery ---

    def discover_entry_points(self) -> None:
        """Load plugins registered as Python entry points."""
        for group, register_fn in [
            ("rag_forge.chunkers", self.register_chunker),
            ("rag_forge.retrievers", self.register_retriever),
            ("rag_forge.metrics", self.register_metric),
        ]:
            eps = importlib.metadata.entry_points(group=group)

            for ep in eps:
                try:
                    cls = ep.load()
                    register_fn(ep.name, cls)
                    _LOG.info("Loaded plugin %s from %s", ep.name, group)
                except Exception as e:
                    _LOG.warning("Failed to load plugin %s from %s: %s", ep.name, group, e)


def get_global_registry() -> PluginRegistry:
    """Get or create the global plugin registry singleton."""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
        _global_registry.discover_entry_points()
    return _global_registry
