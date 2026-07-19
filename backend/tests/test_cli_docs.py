from __future__ import annotations
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch
from typer.testing import CliRunner
from repollama.cli import app


def test_cli_docs_command_success() -> None:
    runner = CliRunner()

    # Create a temporary directory structure to simulate a repo scan
    temp_repo = Path("temp_test_repo")
    temp_repo.mkdir(exist_ok=True)
    try:
        # Create a mock source file
        source_file = temp_repo / "main.py"
        source_file.write_text(
            "class DummyClass:\n    pass\n\ndef dummy_func():\n    pass\n"
        )

        with patch("repollama.llm.ollama.OllamaManager.ping_server", new_callable=AsyncMock) as mock_ping, \
             patch("repollama.llm.ollama.OllamaManager.list_models", new_callable=AsyncMock) as mock_list_models, \
             patch("repollama.agents.documentation.DocumentationAgent.analyze", new_callable=AsyncMock) as mock_analyze:

            mock_ping.return_value = True
            mock_list_models.return_value = ["qwen2.5-coder:latest"]
            mock_analyze.return_value = "# Generated Wiki Content"

            # Execute command: repollama docs temp_test_repo
            result = runner.invoke(app, ["docs", "temp_test_repo"])

            assert result.exit_code == 0
            assert "Developer Portal Artifacts Successfully Generated!" in result.output
            assert "ERD.md" in result.output
            assert "C4.md" in result.output
            assert "WIKI.md" in result.output

            # Check files exist
            docs_dir = Path(".repollama_data/docs")
            assert (docs_dir / "ERD.md").exists()
            assert (docs_dir / "C4.md").exists()
            assert (docs_dir / "WIKI.md").exists()

            # Verify ERD contents
            erd_content = (docs_dir / "ERD.md").read_text()
            assert "DummyClass" in erd_content
            assert "Repository ||--o{ DummyClass : contains" in erd_content

            # Verify WIKI contents
            wiki_content = (docs_dir / "WIKI.md").read_text()
            assert "# Generated Wiki Content" in wiki_content

    finally:
        # Cleanup
        if temp_repo.exists():
            shutil.rmtree(temp_repo)
        docs_dir = Path(".repollama_data/docs")
        if docs_dir.exists():
            shutil.rmtree(docs_dir)
