"""Smoke tests for the observability module."""

from rag_forge_observability.tracing import TracingManager


class TestTracingManager:
    def test_default_disabled(self) -> None:
        manager = TracingManager()
        assert not manager.is_enabled()

    def test_enable(self) -> None:
        manager = TracingManager()
        manager.enable()
        assert manager.is_enabled()

    def test_custom_service_name(self) -> None:
        manager = TracingManager(service_name="my-rag-app")
        assert manager.service_name == "my-rag-app"
