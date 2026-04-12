"""Plugin system for custom RAG-Forge extensions."""

from rag_forge_core.plugins.registry import PluginRegistry, get_global_registry

__all__ = ["PluginRegistry", "get_global_registry"]
