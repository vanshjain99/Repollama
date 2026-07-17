from __future__ import annotations
import asyncio
import shutil
import subprocess
from typing import Any
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from repollama.core.config import settings
from repollama.llm.ollama import OllamaManager
from repollama.engines.ast_parser import ASTParser, UnsupportedLanguageError
from repollama.engines.git_miner import GitMiner, InvalidGitRepositoryError

# Initialize Typer and Rich Console
app = typer.Typer(
    help="Repollama CLI - Headless Python core for local-first system simulation."
)
console = Console()


def check_docker() -> bool:
    """Check if the Docker daemon is currently installed and running.

    Returns:
        bool: True if Docker is running, False otherwise.
    """
    if not shutil.which("docker"):
        return False
    try:
        # Run a quick info check to verify daemon connectivity
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3.0,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


async def get_fastapi_health() -> dict[str, Any] | None:
    """Ping the FastAPI server to retrieve its health status.

    Returns:
        dict: Health details if the server is running, None otherwise.
    """
    url = f"http://{settings.API_HOST}:{settings.API_PORT}/health"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
    except (httpx.ConnectError, httpx.HTTPError, httpx.TimeoutException):
        pass
    return None


async def run_health_check() -> None:
    """Execute health checks for FastAPI, Ollama, and Docker, and display the results."""
    console.print("[bold blue]Running Repollama Health Check...[/bold blue]\n")

    # 1. FastAPI Server Check
    fastapi_status = await get_fastapi_health()

    # 2. Ollama Status Check
    ollama_mgr = OllamaManager(base_url=settings.OLLAMA_BASE_URL)
    ollama_running = await ollama_mgr.ping_server()

    # 3. Docker Status Check
    docker_running = check_docker()

    # Create UI components using Rich
    table = Table(title="System Environment Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")

    # FastAPI row
    if fastapi_status:
        table.add_row(
            "FastAPI Server",
            "[bold green]RUNNING[/bold green]",
            f"http://{settings.API_HOST}:{settings.API_PORT}",
        )
    else:
        table.add_row(
            "FastAPI Server",
            "[bold yellow]OFFLINE[/bold yellow]",
            f"Start with: uvicorn repollama.main:app --host {settings.API_HOST} --port {settings.API_PORT}",
        )

    # Ollama row
    if ollama_running:
        table.add_row(
            "Ollama Host",
            "[bold green]ONLINE[/bold green]",
            f"Base URL: {settings.OLLAMA_BASE_URL}",
        )
    else:
        table.add_row(
            "Ollama Host",
            "[bold red]OFFLINE[/bold red]",
            f"Is Ollama running locally on {settings.OLLAMA_BASE_URL}?",
        )

    # Docker row
    if docker_running:
        table.add_row("Docker Daemon", "[bold green]RUNNING[/bold green]", "")
    else:
        table.add_row(
            "Docker Daemon",
            "[bold yellow]NOT DETECTED[/bold yellow]",
            "Required for sandbox execution environments.",
        )

    console.print(table)
    console.print()

    # Overall Summary Panel
    if ollama_running:
        console.print(
            Panel(
                "[bold green]✓ All core integrations are healthy and ready.[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[bold red]⚠ Some integrations are offline. Please ensure Ollama is running to proceed with code analysis.[/bold red]",
                border_style="red",
            )
        )


async def run_list_models() -> None:
    """Query the Ollama manager and print available models."""
    ollama_mgr = OllamaManager(base_url=settings.OLLAMA_BASE_URL)
    is_up = await ollama_mgr.ping_server()

    if not is_up:
        console.print(
            f"[bold red]Error:[/bold red] Could not connect to Ollama server at {settings.OLLAMA_BASE_URL}."
        )
        console.print(
            "Please ensure Ollama is running and accessible before listing models."
        )
        raise typer.Exit(code=1)

    models = await ollama_mgr.list_models()

    if not models:
        console.print(
            f"[yellow]No models found. Try pulling a model first using 'ollama pull {settings.DEFAULT_MODEL}'.[/yellow]"
        )
        return

    table = Table(title="Available Local Ollama Models")
    table.add_column("Model Name", style="cyan")
    table.add_column("Status", style="green")

    for model in models:
        is_default = " (default)" if model.startswith(settings.DEFAULT_MODEL) else ""
        table.add_row(model, f"Ready{is_default}")

    console.print(table)


@app.command(name="health")
def health_cmd() -> None:
    """Pings the FastAPI server and checks the local system environment (Docker, Ollama)."""
    asyncio.run(run_health_check())


@app.command(name="models")
def models_cmd() -> None:
    """Lists locally available Ollama models."""
    asyncio.run(run_list_models())


@app.command(name="parse")
def parse_cmd(
    file_path: str = typer.Argument(..., help="Path to the source file to parse"),
    json_format: bool = typer.Option(False, "--json", "-j", help="Output in raw JSON format"),
) -> None:
    """Parses a source file using Tree-sitter and prints structural metadata (imports, classes, functions)."""
    parser = ASTParser()
    try:
        metadata = parser.parse_file(file_path)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] File not found: [yellow]{file_path}[/yellow]")
        raise typer.Exit(code=1)
    except UnsupportedLanguageError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    if json_format:
        console.print_json(metadata.model_dump_json())
        return

    # Print a header panel
    console.print(
        Panel(
            f"[bold green]File:[/bold green] {metadata.file_path}\n"
            f"[bold green]Language:[/bold green] {metadata.language.upper()}\n"
            f"[bold green]Metrics:[/bold green] {len(metadata.imports)} imports, "
            f"{len(metadata.classes)} classes, {len(metadata.functions)} functions",
            title="[bold blue]AST Analysis Results[/bold blue]",
            border_style="blue",
        )
    )

    # 1. Imports
    if metadata.imports:
        table_imports = Table(title="Extracted Imports", show_header=True, header_style="bold magenta")
        table_imports.add_column("Import Statement", style="cyan")
        for imp in metadata.imports:
            table_imports.add_row(imp)
        console.print(table_imports)
        console.print()
    else:
        console.print("[dim italic]No imports found.[/dim italic]\n")

    # 2. Classes
    if metadata.classes:
        table_classes = Table(title="Extracted Classes", show_header=True, header_style="bold magenta")
        table_classes.add_column("Class Name", style="bold green")
        table_classes.add_column("Start Line", style="yellow", justify="right")
        table_classes.add_column("End Line", style="yellow", justify="right")
        table_classes.add_column("Lines", style="blue", justify="right")
        for cls in metadata.classes:
            lines_cnt = cls.end_line - cls.start_line + 1
            table_classes.add_row(cls.name, str(cls.start_line), str(cls.end_line), str(lines_cnt))
        console.print(table_classes)
        console.print()
    else:
        console.print("[dim italic]No classes found.[/dim italic]\n")

    # 3. Functions / Methods
    if metadata.functions:
        table_funcs = Table(title="Extracted Functions & Methods", show_header=True, header_style="bold magenta")
        table_funcs.add_column("Function / Method Name", style="bold cyan")
        table_funcs.add_column("Start Line", style="yellow", justify="right")
        table_funcs.add_column("End Line", style="yellow", justify="right")
        table_funcs.add_column("Lines", style="blue", justify="right")
        for func in metadata.functions:
            lines_cnt = func.end_line - func.start_line + 1
            table_funcs.add_row(func.name, str(func.start_line), str(func.end_line), str(lines_cnt))
        console.print(table_funcs)
    else:
        console.print("[dim italic]No functions or methods found.[/dim italic]\n")


@app.command(name="git")
def git_cmd(
    repo_path: str = typer.Argument(".", help="Path to the target Git repository"),
) -> None:
    """Analyze the Git repository at <repo_path> to print evolutionary metadata, recent history, and file churn."""
    try:
        miner = GitMiner(repo_path)
    except InvalidGitRepositoryError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    # 1. Retrieve data
    metadata = miner.get_repository_metadata()
    commit_history = miner.get_commit_history(limit=5)
    churn = miner.get_file_churn(limit=10)

    # 2. Print Repository Metadata
    meta_info = (
        f"[bold cyan]Active Branch:[/bold cyan] {metadata['active_branch']}\n"
        f"[bold cyan]Total Commits:[/bold cyan] {metadata['commit_count']}\n"
        f"[bold cyan]Local Branches:[/bold cyan] {', '.join(metadata['local_branches'])}"
    )
    console.print(
        Panel(
            meta_info,
            title="[bold blue]Repository Metadata[/bold blue]",
            border_style="blue",
            expand=False,
        )
    )
    console.print()

    # 3. Print Recent Commits Table
    table_commits = Table(title="Recent Commits (Last 5)", show_header=True, header_style="bold magenta")
    table_commits.add_column("Hash", style="yellow")
    table_commits.add_column("Author", style="cyan")
    table_commits.add_column("Message", style="green")

    if commit_history:
        for commit in commit_history:
            table_commits.add_row(commit["hash"], commit["author"], commit["message"])
    else:
        table_commits.add_row("[dim]N/A[/dim]", "[dim]N/A[/dim]", "[dim]No commits found[/dim]")
    console.print(table_commits)
    console.print()

    # 4. Print Top 10 Most Churned Files Table
    table_churn = Table(title="Top 10 Most Churned Files", show_header=True, header_style="bold magenta")
    table_churn.add_column("File Path", style="cyan")
    table_churn.add_column("Edit Count", style="yellow", justify="right")

    if churn:
        for file_path, count in churn.items():
            table_churn.add_row(file_path, str(count))
    else:
        table_churn.add_row("[dim]No file changes tracked[/dim]", "0")
    console.print(table_churn)


@app.command(name="index")
def index_cmd(
    repo_path: str = typer.Argument(".", help="Path to the target repository to index"),
) -> None:
    """Index the codebase in <repo_path> into the Knowledge Graph and Vector Store."""
    from repollama.engines.graph_builder import KnowledgeGraphBuilder
    from repollama.database.vector_store import LocalVectorStore
    from pathlib import Path

    target_dir = Path(repo_path).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        console.print(
            f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{repo_path}[/yellow]"
        )
        raise typer.Exit(code=1)

    console.print(f"[bold blue]Indexing repository at:[/bold blue] {target_dir}")

    # Initialize components
    parser = ASTParser()
    graph_builder = KnowledgeGraphBuilder()
    vector_store = LocalVectorStore()

    # Define excluded directories
    exclude_dirs = {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        ".repollama_data",
        ".pytest_cache",
        ".mypy_cache",
    }

    supported_extensions = {".py", ".js", ".jsx", ".ts", ".tsx"}
    indexed_files_count = 0

    # Recursive directory walk
    for path_obj in target_dir.rglob("*"):
        if not path_obj.is_file():
            continue

        # Check if any parent directory is in exclude_dirs
        relative_path = path_obj.relative_to(target_dir)
        if any(part in exclude_dirs for part in relative_path.parts):
            continue

        if path_obj.suffix.lower() not in supported_extensions:
            continue

        file_path_str = str(relative_path)

        try:
            # Parse the AST metadata
            ast_meta = parser.parse_file(path_obj)

            # 1. Populate the Knowledge Graph
            graph_builder.add_file_node(file_path_str, {"language": ast_meta.language})

            for cls in ast_meta.classes:
                graph_builder.add_code_node(cls.name, "class", file_path_str)

            for func in ast_meta.functions:
                graph_builder.add_code_node(func.name, "function", file_path_str)

            for imp in ast_meta.imports:
                graph_builder.add_import_edge(file_path_str, imp)

            # 2. Populate the Vector Store
            classes_str = ", ".join([c.name for c in ast_meta.classes]) if ast_meta.classes else "none"
            functions_str = ", ".join([f.name for f in ast_meta.functions]) if ast_meta.functions else "none"
            imports_str = ", ".join(ast_meta.imports) if ast_meta.imports else "none"
            text_repr = (
                f"File {file_path_str} is written in {ast_meta.language}. "
                f"It contains classes: {classes_str}. "
                f"It contains functions: {functions_str}. "
                f"It imports: {imports_str}."
            )

            vector_store.add_document(
                doc_id=file_path_str,
                text=text_repr,
                metadata={"file_path": file_path_str, "language": ast_meta.language},
            )

            indexed_files_count += 1

        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Failed to index {file_path_str}: {e}")

    # Retrieve stats
    graph_stats = graph_builder.get_graph_stats()
    try:
        vs_size = vector_store.collection.count()
    except Exception:
        vs_size = 0

    # Print success panel
    stats_content = (
        f"[bold green]Total Files Indexed:[/bold green] {indexed_files_count}\n"
        f"[bold green]Knowledge Graph Nodes:[/bold green] {graph_stats['node_count']}\n"
        f"[bold green]Knowledge Graph Edges:[/bold green] {graph_stats['edge_count']}\n"
        f"[bold green]Vector Store Collection Size:[/bold green] {vs_size}"
    )
    console.print()
    console.print(
        Panel(
            stats_content,
            title="[bold green]✓ Indexing Completed[/bold green]",
            border_style="green",
            expand=False,
        )
    )


if __name__ == "__main__":
    app()

