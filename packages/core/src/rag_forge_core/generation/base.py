"""Base protocol for LLM generation providers."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class GenerationProvider(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...
    def model_name(self) -> str: ...
