from repollama.agents.base import BaseAgent

class ReviewerAgent(BaseAgent):
    """Staff Engineer agent who reviews, polishes, and refines specialist draft reports."""

    async def analyze(self, context: dict) -> str:
        raise NotImplementedError("ReviewerAgent does not use the default analyze method. Use review instead.")

    async def review(self, agent_name: str, draft_report: str) -> str:
        prompt = (
            "You are a strict Staff Engineer reviewing a junior engineer's draft report.\n"
            f"Agent Name: {agent_name}\n"
            f"Draft Report:\n---\n{draft_report}\n---\n\n"
            "Verify if the draft report sounds hallucinated, overly generic, or lacking structural detail.\n"
            "Refine, format, and polish the report into a highly detailed, professional, and rigorous production-grade analysis.\n"
            "Keep the tone professional and return ONLY the final polished report."
        )
        return await self.ollama_manager.generate(prompt, self.model)
