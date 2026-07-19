import asyncio
from repollama.llm.ollama import OllamaManager
from repollama.agents.specialists import ArchitectureAgent, SecurityAgent
from repollama.agents.reviewer import ReviewerAgent
from repollama.core.config import settings

class AgentCoordinator:
    """Orchestrates specialist agents concurrently and passes their drafts through review."""

    def __init__(self, ollama_manager: OllamaManager, model: str = settings.DEFAULT_MODEL) -> None:
        self.ollama_manager = ollama_manager
        self.model = model

    async def run_audit(self, context: dict) -> dict[str, str]:
        arch_agent = ArchitectureAgent(self.ollama_manager, self.model)
        sec_agent = SecurityAgent(self.ollama_manager, self.model)
        reviewer = ReviewerAgent(self.ollama_manager, self.model)

        # Run analysis concurrently
        arch_draft, sec_draft = await asyncio.gather(
            arch_agent.analyze(context),
            sec_agent.analyze(context)
        )

        # Review drafts sequentially
        final_arch = await reviewer.review("Architecture Agent", arch_draft)
        final_sec = await reviewer.review("Security Agent", sec_draft)

        return {
            "architecture": final_arch,
            "security": final_sec
        }
