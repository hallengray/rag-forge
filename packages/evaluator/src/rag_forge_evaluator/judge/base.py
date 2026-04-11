"""Base protocol for LLM judge providers."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class JudgeProvider(Protocol):
    """Protocol for LLM judges that score RAG pipeline outputs."""

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt to the LLM judge and return the response text."""
        ...

    def model_name(self) -> str:
        """Return the name of the judge model."""
        ...
