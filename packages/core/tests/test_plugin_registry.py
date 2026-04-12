"""Tests for the plugin registry."""

from rag_forge_core.plugins.registry import PluginRegistry, get_global_registry


class TestPluginRegistry:
    def test_register_and_get_chunker(self) -> None:
        registry = PluginRegistry()

        class FakeChunker:
            pass

        registry.register_chunker("fake", FakeChunker)
        assert registry.get_chunker("fake") is FakeChunker

    def test_get_unknown_chunker_returns_none(self) -> None:
        registry = PluginRegistry()
        assert registry.get_chunker("nonexistent") is None

    def test_register_and_get_retriever(self) -> None:
        registry = PluginRegistry()

        class FakeRetriever:
            pass

        registry.register_retriever("fake", FakeRetriever)
        assert registry.get_retriever("fake") is FakeRetriever

    def test_register_and_get_metric(self) -> None:
        registry = PluginRegistry()

        class FakeMetric:
            pass

        registry.register_metric("fake", FakeMetric)
        assert registry.get_metric("fake") is FakeMetric

    def test_list_chunkers(self) -> None:
        registry = PluginRegistry()

        class A:
            pass

        class B:
            pass

        registry.register_chunker("a", A)
        registry.register_chunker("b", B)
        names = registry.list_chunkers()
        assert set(names) == {"a", "b"}

    def test_list_retrievers(self) -> None:
        registry = PluginRegistry()
        assert registry.list_retrievers() == []

    def test_list_metrics(self) -> None:
        registry = PluginRegistry()
        assert registry.list_metrics() == []

    def test_duplicate_registration_overwrites(self) -> None:
        registry = PluginRegistry()

        class V1:
            pass

        class V2:
            pass

        registry.register_chunker("x", V1)
        registry.register_chunker("x", V2)
        assert registry.get_chunker("x") is V2

    def test_global_registry_singleton(self) -> None:
        r1 = get_global_registry()
        r2 = get_global_registry()
        assert r1 is r2
