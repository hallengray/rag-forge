"""Tests for the generation providers and query engine."""

from rag_forge_core.generation.base import GenerationProvider
from rag_forge_core.generation.mock_generator import MockGenerator


class TestMockGenerator:
    def test_implements_protocol(self) -> None:
        assert isinstance(MockGenerator(), GenerationProvider)

    def test_returns_fixed_response(self) -> None:
        gen = MockGenerator(fixed_response="The answer is 42.")
        assert gen.generate("system", "user") == "The answer is 42."

    def test_default_response(self) -> None:
        assert len(MockGenerator().generate("system", "question")) > 0

    def test_model_name(self) -> None:
        assert MockGenerator().model_name() == "mock-generator"
