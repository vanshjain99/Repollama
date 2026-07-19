from repollama.agents.base import BaseAgent

class ArchitectureAgent(BaseAgent):
    """Specialist agent focused on analyzing repository architecture."""

    async def analyze(self, context: dict) -> str:
        graph_stats = context.get("graph_stats", {})
        stack_info = context.get("stack_info", {})

        prompt = (
            "You are a Principal Architect. Analyze the following project structure, stack, and graph details:\n"
            f"Graph Statistics: {graph_stats}\n"
            f"Technology Stack: {stack_info}\n\n"
            "Deduce the architectural pattern (e.g. MVC, Microservices, Layered, Hexagonal, etc.).\n"
            "Identify the Strengths and Weaknesses of the architectural pattern in this context.\n"
            "Ensure your analysis is structured, clear, and detailed."
        )
        return await self.ollama_manager.generate(prompt, self.model)


class SecurityAgent(BaseAgent):
    """Specialist agent focused on identifying threat boundaries and security vulnerabilities."""

    async def analyze(self, context: dict) -> str:
        secrets_warnings = context.get("secrets_warnings", [])
        network_traffic = context.get("network_traffic", [])

        prompt = (
            "You are a Security Auditor. Analyze the following threat signals:\n"
            f"Secrets Warnings: {secrets_warnings}\n"
            f"Intercepted Network Traffic: {network_traffic}\n\n"
            "Identify potential threat boundaries, vulnerabilities, or data leak vectors.\n"
            "Flag high-risk configurations or practices and provide remediation advice.\n"
            "Ensure your analysis is structured, clear, and detailed."
        )
        return await self.ollama_manager.generate(prompt, self.model)
