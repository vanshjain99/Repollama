from __future__ import annotations
from unittest.mock import AsyncMock, patch, MagicMock
from typer.testing import CliRunner
from repollama.cli import app


def test_cli_record_command_success() -> None:
    runner = CliRunner()

    with patch("repollama.engines.browser.BrowserAgent") as MockBrowserAgent:
        # Configure mock agent instance
        mock_agent_instance = MagicMock()
        mock_agent_instance.__aenter__ = AsyncMock(return_value=mock_agent_instance)
        mock_agent_instance.__aexit__ = AsyncMock(return_value=None)
        mock_agent_instance.navigate = AsyncMock()
        mock_agent_instance.record_workflow = AsyncMock(return_value="/absolute/path/to/workflow.webm")

        MockBrowserAgent.return_value = mock_agent_instance

        # Execute command: repollama record http://localhost:8000 "Login,Submit,View Profile"
        result = runner.invoke(app, ["record", "http://localhost:8000", "Login,Submit,View Profile"])

        # Assertions
        assert result.exit_code == 0
        assert "Workflow recording completed successfully!" in result.output
        assert "Sequence of actions executed" in result.output
        assert "Login" in result.output
        assert "Submit" in result.output
        assert "View Profile" in result.output
        assert "/absolute/path/to/workflow.webm" in result.output

        # Verify calls
        MockBrowserAgent.assert_called_once_with(record_video_dir=".repollama_data/videos")
        mock_agent_instance.navigate.assert_called_once_with("http://localhost:8000")
        mock_agent_instance.record_workflow.assert_called_once_with(["Login", "Submit", "View Profile"], output_filename="workflow.webm")


def test_cli_record_command_navigation_failure() -> None:
    runner = CliRunner()

    with patch("repollama.engines.browser.BrowserAgent") as MockBrowserAgent:
        mock_agent_instance = MagicMock()
        mock_agent_instance.__aenter__ = MagicMock()
        mock_agent_instance.__aenter__.return_value = mock_agent_instance
        # Under async context manager, __aenter__ is awaited, so make it an AsyncMock
        mock_agent_instance.__aenter__ = AsyncMock(return_value=mock_agent_instance)
        mock_agent_instance.__aexit__ = AsyncMock(return_value=None)
        mock_agent_instance.navigate = AsyncMock(side_effect=Exception("Connection timed out"))

        MockBrowserAgent.return_value = mock_agent_instance

        result = runner.invoke(app, ["record", "http://localhost:8000", "Login"])

        assert result.exit_code == 1
        assert "Failed to navigate to http://localhost:8000" in result.output


def test_cli_record_command_workflow_failure() -> None:
    runner = CliRunner()

    with patch("repollama.engines.browser.BrowserAgent") as MockBrowserAgent:
        mock_agent_instance = MagicMock()
        mock_agent_instance.__aenter__ = AsyncMock(return_value=mock_agent_instance)
        mock_agent_instance.__aexit__ = AsyncMock(return_value=None)
        mock_agent_instance.navigate = AsyncMock()
        mock_agent_instance.record_workflow = AsyncMock(side_effect=Exception("Playwright context crashed"))

        MockBrowserAgent.return_value = mock_agent_instance

        result = runner.invoke(app, ["record", "http://localhost:8000", "Login"])

        assert result.exit_code == 1
        assert "Workflow execution or video generation failed" in result.output
