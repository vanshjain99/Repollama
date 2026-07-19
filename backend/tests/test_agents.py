from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from repollama.llm.ollama import OllamaManager
from repollama.agents.base import BaseAgent
from repollama.agents.specialists import ArchitectureAgent, SecurityAgent
from repollama.agents.reviewer import ReviewerAgent
from repollama.agents.coordinator import AgentCoordinator
from repollama.cli import app
from typer.testing import CliRunner


# Helper to subclass BaseAgent for testing
class MockAgent(BaseAgent):
    async def analyze(self, context: dict) -> str:
        return f"Mock analyze result with context keys: {list(context.keys())}"


def test_base_agent_init() -> None:
    mock_ollama = MagicMock(spec=OllamaManager)
    agent = MockAgent(ollama_manager=mock_ollama, model="test-model")
    assert agent.ollama_manager == mock_ollama
    assert agent.model == "test-model"


@pytest.mark.anyio
async def test_base_agent_analyze() -> None:
    mock_ollama = MagicMock(spec=OllamaManager)
    agent = MockAgent(ollama_manager=mock_ollama, model="test-model")
    res = await agent.analyze({"key": "value"})
    assert "Mock analyze result" in res
    assert "key" in res


@pytest.mark.anyio
async def test_architecture_agent_analyze() -> None:
    mock_ollama = AsyncMock(spec=OllamaManager)
    mock_ollama.generate.return_value = "Architecture analysis draft"

    agent = ArchitectureAgent(ollama_manager=mock_ollama, model="test-model")
    context = {
        "graph_stats": {"nodes": 10, "edges": 15},
        "stack_info": {"language": "Python"}
    }

    result = await agent.analyze(context)
    assert result == "Architecture analysis draft"
    
    # Check that generate was called with a prompt containing graph stats and stack info
    mock_ollama.generate.assert_called_once()
    prompt = mock_ollama.generate.call_args[0][0]
    assert "Principal Architect" in prompt
    assert "{'nodes': 10, 'edges': 15}" in prompt
    assert "{'language': 'Python'}" in prompt
    assert mock_ollama.generate.call_args[0][1] == "test-model"


@pytest.mark.anyio
async def test_security_agent_analyze() -> None:
    mock_ollama = AsyncMock(spec=OllamaManager)
    mock_ollama.generate.return_value = "Security analysis draft"

    agent = SecurityAgent(ollama_manager=mock_ollama, model="test-model")
    context = {
        "secrets_warnings": ["exposed key"],
        "network_traffic": [{"url": "http://leak.com"}]
    }

    result = await agent.analyze(context)
    assert result == "Security analysis draft"
    
    mock_ollama.generate.assert_called_once()
    prompt = mock_ollama.generate.call_args[0][0]
    assert "Security Auditor" in prompt
    assert "['exposed key']" in prompt
    assert "http://leak.com" in prompt


@pytest.mark.anyio
async def test_documentation_agent_analyze() -> None:
    from repollama.agents.documentation import DocumentationAgent
    mock_ollama = AsyncMock(spec=OllamaManager)
    mock_ollama.generate.return_value = "Mock WIKI Content"

    agent = DocumentationAgent(ollama_manager=mock_ollama, model="test-model")
    context = {
        "repo_stats": {
            "repo_name": "TestRepo",
            "total_files": 10,
            "total_classes": 5,
        }
    }

    result = await agent.analyze(context)
    assert result == "Mock WIKI Content"

    mock_ollama.generate.assert_called_once()
    prompt = mock_ollama.generate.call_args[0][0]
    assert "expert Technical Writer" in prompt
    assert "1. Introduction" in prompt
    assert "2. Architecture" in prompt
    assert "3. Getting Started" in prompt
    assert "TestRepo" in prompt
    assert "10" in prompt
    assert "5" in prompt


@pytest.mark.anyio
async def test_reviewer_agent_review() -> None:
    mock_ollama = AsyncMock(spec=OllamaManager)
    mock_ollama.generate.return_value = "Polished report content"

    agent = ReviewerAgent(ollama_manager=mock_ollama, model="test-model")
    
    with pytest.raises(NotImplementedError):
        await agent.analyze({})

    result = await agent.review("TestAgent", "Draft content to review")
    assert result == "Polished report content"

    mock_ollama.generate.assert_called_once()
    prompt = mock_ollama.generate.call_args[0][0]
    assert "strict Staff Engineer" in prompt
    assert "TestAgent" in prompt
    assert "Draft content to review" in prompt


@pytest.mark.anyio
async def test_agent_coordinator_run_audit() -> None:
    mock_ollama = AsyncMock(spec=OllamaManager)
    
    # We mock generate to return distinct values based on the prompt content
    def generate_side_effect(prompt: str, model: str) -> str:
        if "Principal Architect" in prompt:
            return "Architecture draft report"
        elif "Security Auditor" in prompt:
            return "Security draft report"
        elif "Architecture Agent" in prompt:
            return "Final Architecture Report"
        elif "Security Agent" in prompt:
            return "Final Security Report"
        return "Default"

    mock_ollama.generate.side_effect = generate_side_effect

    coordinator = AgentCoordinator(ollama_manager=mock_ollama, model="test-model")
    context = {
        "graph_stats": {"nodes": 10},
        "stack_info": {"language": "Python"},
        "secrets_warnings": ["exposed key"],
        "network_traffic": []
    }

    result = await coordinator.run_audit(context)
    
    assert result["architecture"] == "Final Architecture Report"
    assert result["security"] == "Final Security Report"
    assert mock_ollama.generate.call_count == 4


def test_cli_audit_command_success() -> None:
    runner = CliRunner()

    with patch("repollama.llm.ollama.OllamaManager.ping_server", new_callable=AsyncMock) as mock_ping, \
         patch("repollama.llm.ollama.OllamaManager.list_models", new_callable=AsyncMock) as mock_list_models, \
         patch("repollama.agents.coordinator.AgentCoordinator.run_audit", new_callable=AsyncMock) as mock_run_audit:
         
        mock_ping.return_value = True
        mock_list_models.return_value = ["qwen2.5-coder:latest"]
        mock_run_audit.return_value = {
            "architecture": "Polished Arch Report Summary",
            "security": "Polished Sec Report Summary"
        }

        # Invoke CLI command: repollama audit
        result = runner.invoke(app, ["audit"])

        assert result.exit_code == 0
        assert "Starting Repository Audit Crew..." in result.output
        assert "Architecture Audit Report" in result.output
        assert "Polished Arch Report Summary" in result.output
        assert "Security Audit Report" in result.output
        assert "Polished Sec Report Summary" in result.output

        mock_ping.assert_called_once()
        mock_list_models.assert_called_once()
        mock_run_audit.assert_called_once()


def test_cli_audit_command_ollama_offline() -> None:
    runner = CliRunner()

    with patch("repollama.llm.ollama.OllamaManager.ping_server", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = False

        result = runner.invoke(app, ["audit"])

        assert result.exit_code == 1
        assert "Error: Could not connect to local Ollama server" in result.output


def test_cli_audit_command_audit_failure() -> None:
    runner = CliRunner()

    with patch("repollama.llm.ollama.OllamaManager.ping_server", new_callable=AsyncMock) as mock_ping, \
         patch("repollama.llm.ollama.OllamaManager.list_models", new_callable=AsyncMock) as mock_list_models, \
         patch("repollama.agents.coordinator.AgentCoordinator.run_audit", new_callable=AsyncMock) as mock_run_audit:
         
        mock_ping.return_value = True
        mock_list_models.return_value = ["qwen2.5-coder:latest"]
        mock_run_audit.side_effect = Exception("Ollama disconnected during prompt evaluation")

        result = runner.invoke(app, ["audit"])

        assert result.exit_code == 1
        assert "Audit Error" in result.output
        assert "✘ Audit Crew Failed!" in result.output
        assert "Ollama disconnected during prompt evaluation" in result.output

