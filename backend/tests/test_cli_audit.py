from __future__ import annotations
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch
from typer.testing import CliRunner
from repollama.cli import app


def test_cli_audit_command_success() -> None:
    runner = CliRunner()

    temp_repo = Path("temp_test_audit_repo")
    temp_repo.mkdir(exist_ok=True)
    try:
        source_file = temp_repo / "app.py"
        source_file.write_text(
            "import os\n\nclass Server:\n    def start(self):\n        pass\n"
        )

        with patch("repollama.llm.ollama.OllamaManager.ping_server", new_callable=AsyncMock) as mock_ping, \
             patch("repollama.llm.ollama.OllamaManager.list_models", new_callable=AsyncMock) as mock_list_models, \
             patch("repollama.agents.coordinator.AgentCoordinator.run_audit", new_callable=AsyncMock) as mock_run_audit:

            mock_ping.return_value = True
            mock_list_models.return_value = ["qwen2.5-coder:latest"]
            mock_run_audit.return_value = {
                "architecture": "Architecture looks solid.",
                "security": "No major security threats found."
            }

            result = runner.invoke(app, ["audit", "temp_test_audit_repo"])

            assert result.exit_code == 0
            assert "Architecture Audit Report" in result.output
            assert "Security Audit Report" in result.output

            mock_run_audit.assert_called_once()
            passed_context = mock_run_audit.call_args[0][0]

            assert "graph_stats" in passed_context
            assert "stack_info" in passed_context
            assert "missing_secrets" in passed_context
            assert "security_threats" in passed_context
            assert "performance_bottlenecks" in passed_context
            assert passed_context["graph_stats"]["nodes"] >= 1

    finally:
        if temp_repo.exists():
            shutil.rmtree(temp_repo)
