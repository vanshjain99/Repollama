from abc import ABC, abstractmethod
from repollama.llm.ollama import OllamaManager
from repollama.core.config import settings

class BaseAgent(ABC):
    """Abstract Base Agent utilizing local OllamaManager for LLM generation."""

    def __init__(self, ollama_manager: OllamaManager, model: str = settings.DEFAULT_MODEL) -> None:
        self.ollama_manager = ollama_manager
        self.model = model

    @abstractmethod
    async def analyze(self, context: dict) -> str:
        """Asynchronously analyze the provided context and return a draft report."""
        pass
