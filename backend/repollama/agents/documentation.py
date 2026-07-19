from __future__ import annotations
from repollama.agents.base import BaseAgent


class DocumentationAgent(BaseAgent):
    """Technical Writer agent that writes comprehensive system design and wiki documentation."""

    async def analyze(self, context: dict) -> str:
        """Analyze the repository metadata and return the generated wiki documentation.

        Args:
            context: Dictionary containing repository metadata (Graph & Audit data).

        Returns:
            str: Generated Markdown documentation.
        """
        prompt = (
            "You are an expert Technical Writer. Your task is to write a 3-section README.md "
            "(Introduction, Architecture, Getting Started) based on the provided repository metadata context "
            "(including Graph/Audit data if available):\n"
            f"{context}\n\n"
            "The documentation must contain exactly the following three sections:\n"
            "1. Introduction: A clear explanation of what the system does, its goals, and target audience.\n"
            "2. Architecture: An overview of the system structure, design patterns, and internal components.\n"
            "3. Getting Started: Step-by-step instructions on setting up, building, and running the system.\n\n"
            "Write the documentation in clean, detailed, and professional Markdown. Do not include any meta-commentary, "
            "just the generated markdown content."
        )
        return await self.ollama_manager.generate(prompt, self.model)
