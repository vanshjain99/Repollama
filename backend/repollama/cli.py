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
from repollama.engines.sandbox import EnvironmentDetector, DockerSandbox
import time


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


@app.command(name="sandbox")
def sandbox_cmd(
    repo_path: str = typer.Argument(".", help="Path to the repository to sandbox"),
) -> None:
    """Detect repository environment and run it in a secure Docker sandbox container."""
    from pathlib import Path

    target_dir = Path(repo_path).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        console.print(
            f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{repo_path}[/yellow]"
        )
        raise typer.Exit(code=1)

    console.print(f"[bold blue]Analyzing repository at:[/bold blue] {target_dir}")

    # 1. Environment Detection
    detector = EnvironmentDetector(target_dir)
    stack_info = detector.detect_stack()
    secrets_info = detector.detect_secrets()

    # Create Stack Panel
    stack_details = (
        f"[bold cyan]Detected Stack:[/bold cyan] {stack_info['stack']}\n"
        f"[bold cyan]Primary Language:[/bold cyan] {stack_info['language'].upper()}\n"
        f"[bold cyan]Dockerfile:[/bold cyan] {'[green]Yes[/green]' if stack_info['has_dockerfile'] else '[yellow]No[/yellow]'}\n"
        f"[bold cyan]Docker Compose:[/bold cyan] {'[green]Yes[/green]' if stack_info['has_docker_compose'] else '[yellow]No[/yellow]'}"
    )
    if stack_info["start_scripts"]:
        scripts_str = ", ".join(stack_info["start_scripts"])
        stack_details += f"\n[bold cyan]Start Scripts:[/bold cyan] {scripts_str}"

    console.print(
        Panel(
            stack_details,
            title="[bold blue]Environment Detection[/bold blue]",
            border_style="blue",
            expand=False,
        )
    )

    # 2. Secrets / Env Check Warning Panel
    if secrets_info:
        warning_content = (
            f"[bold yellow]⚠ {secrets_info['warning']}[/bold yellow]\n\n"
            "The following environment variables are required but missing:\n"
        )
        for key in secrets_info["missing_keys"]:
            warning_content += f" - {key}\n"
        console.print(
            Panel(
                warning_content.strip(),
                title="[bold yellow]Configuration Warning[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

    # 3. Docker Sandbox Control
    console.print("\n[bold blue]Initializing Docker Sandbox...[/bold blue]")
    sandbox = DockerSandbox()
    if not sandbox.is_available:
        console.print(
            Panel(
                "[bold red]Error: Docker daemon is not running.[/bold red]\n\n"
                "To run the runtime simulation, please start [bold]Docker Desktop[/bold] "
                "or ensure the Docker daemon is accessible in your environment.",
                title="[bold red]Docker Unavailable[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        raise typer.Exit(code=1)

    console.print("[green]✔ Docker daemon detected and responsive.[/green]")
    console.print("[bold yellow]Starting sandbox container...[/bold yellow]")

    try:
        sandbox_res = sandbox.start_sandbox(target_dir, stack_info)
        container_id = sandbox_res["container_id"]
        host_port = sandbox_res["host_port"]

        # Display Success Panel
        short_id = container_id[:12]
        port_details = f"port [bold cyan]{host_port}[/bold cyan]" if host_port else "no mapped ports"
        success_content = (
            f"[bold green]✔ Container successfully started![/bold green]\n\n"
            f"[bold]Container ID:[/bold] {short_id}\n"
            f"[bold]Host Port Mapping:[/bold] {port_details}\n"
            f"[bold]Mount Path:[/bold] /app -> {target_dir}"
        )
        console.print(
            Panel(
                success_content,
                title="[bold green]Sandbox Active[/bold green]",
                border_style="green",
                expand=False,
            )
        )

        console.print("\n[bold yellow]Press Ctrl+C to stop the sandbox container and cleanup...[/bold yellow]")

        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[bold blue]Shutting down sandbox container...[/bold blue]")

    except Exception as e:
        console.print(f"[bold red]Error starting sandbox container:[/bold red] {e}")
        raise typer.Exit(code=1)
    finally:
        # Stop and cleanup container
        if 'container_id' in locals():
            sandbox.stop_sandbox(container_id)
            console.print("[bold green]✔ Sandbox container cleaned up successfully.[/bold green]")


@app.command(name="browse")
def browse_cmd(
    url: str = typer.Argument(..., help="Target URL to browse and analyze"),
) -> None:
    """Navigate to a target URL, extract interactive elements, and capture a screenshot."""
    async def run_browser() -> None:
        from repollama.engines.browser import BrowserAgent
        from rich.panel import Panel
        from rich.table import Table
        import os

        console.print(f"[bold blue]Navigating to URL:[/bold blue] {url}")

        async with BrowserAgent() as agent:
            try:
                await agent.navigate(url)
                title = await agent.page.title()
            except Exception as e:
                console.print(f"[bold red]Failed to navigate or read title:[/bold red] {e}")
                raise typer.Exit(code=1)

            # Extract elements
            elements = await agent.extract_interactive_elements()

            # Save screenshot
            screenshot_path = ".repollama_data/screenshots/test_capture.png"
            try:
                await agent.capture_screenshot(screenshot_path)
            except Exception as e:
                console.print(f"[bold yellow]Warning: Failed to capture screenshot:[/bold yellow] {e}")

            # Print success panel
            console.print(
                Panel(
                    f"[bold green]✔ Successfully analyzed page![/bold green]\n\n"
                    f"[bold]Page Title:[/bold] {title}\n"
                    f"[bold]URL:[/bold] {url}",
                    title="[bold blue]Browser Simulation[/bold blue]",
                    border_style="blue",
                    expand=False,
                )
            )

            # Create Table of interactive elements
            table = Table(title="Discovered Interactive Elements")
            table.add_column("Category", style="cyan")
            table.add_column("Count", style="magenta", justify="right")
            table.add_column("Details/Names", style="green")

            # Format Buttons
            btn_names = [b["text"] for b in elements["buttons"] if b["text"]]
            btn_details = ", ".join(btn_names[:10])
            if len(btn_names) > 10:
                btn_details += f" ... (+{len(btn_names) - 10} more)"
            if not btn_details:
                btn_details = "[dim italic]No buttons with text[/dim italic]"
            table.add_row("Buttons", str(len(elements["buttons"])), btn_details)

            # Format Links
            link_names = [l["text"] for l in elements["links"] if l["text"]]
            link_details = ", ".join(link_names[:10])
            if len(link_names) > 10:
                link_details += f" ... (+{len(link_names) - 10} more)"
            if not link_details:
                link_details = "[dim italic]No links with text[/dim italic]"
            table.add_row("Links", str(len(elements["links"])), link_details)

            # Format Inputs
            input_names = [i["name"] or i["placeholder"] or f"<{i['type']}>" for i in elements["inputs"]]
            input_details = ", ".join(input_names[:10])
            if len(input_names) > 10:
                input_details += f" ... (+{len(input_names) - 10} more)"
            if not input_details:
                input_details = "[dim italic]No inputs[/dim italic]"
            table.add_row("Inputs/Forms", str(len(elements["inputs"])), input_details)

            console.print(table)

            # Intercepted network traffic
            network_traffic = agent.get_network_traffic()
            if network_traffic:
                traffic_table = Table(title="Intercepted API Traffic (Fetch/XHR)")
                traffic_table.add_column("Method", style="bold cyan")
                traffic_table.add_column("Resource Type", style="magenta")
                traffic_table.add_column("URL", style="yellow")

                for item in network_traffic:
                    url_str = item["url"]
                    if len(url_str) > 60:
                        url_str = url_str[:57] + "..."
                    traffic_table.add_row(item["method"], item["resource_type"], url_str)
                console.print(traffic_table)
            else:
                console.print("\n[bold yellow]No API traffic detected[/bold yellow]")

            # Print screenshot path
            abs_screenshot_path = os.path.abspath(screenshot_path)
            console.print(f"\n[bold green]Screenshot saved to:[/bold green] {abs_screenshot_path}")

    try:
        asyncio.run(run_browser())
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]An error occurred during browsing execution:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="trace")
def trace_cmd(
    url: str = typer.Argument(..., help="Target URL to navigate to"),
    click_text: str = typer.Argument(..., help="Text of the element to click and trace"),
) -> None:
    """Trace a user click action and generate a Mermaid sequence diagram of the resulting network traffic."""
    async def run_trace() -> None:
        from repollama.engines.browser import BrowserAgent
        from repollama.engines.sequence_builder import SequenceDiagramBuilder

        console.print(f"[bold blue]Navigating to URL:[/bold blue] {url}")

        async with BrowserAgent() as agent:
            try:
                await agent.navigate(url)
            except Exception as e:
                console.print(f"[bold red]Failed to navigate to {url}:[/bold red] {e}")
                raise typer.Exit(code=1)

            console.print(f"[bold blue]Attempting to click element containing text:[/bold blue] '{click_text}'")
            try:
                result = await agent.click_and_trace(click_text)
            except ValueError as e:
                console.print(f"[bold red]Click trace failed:[/bold red] {e}")
                raise typer.Exit(code=1)
            except Exception as e:
                console.print(f"[bold red]Unexpected error during click trace:[/bold red] {e}")
                raise typer.Exit(code=1)

            # Generate diagram
            mermaid_diagram = SequenceDiagramBuilder.generate(result["action"], result["traffic"])

            # Print success message and the Mermaid diagram in a Panel
            console.print("[bold green]✓ Click and trace completed successfully![/bold green]")
            console.print(
                Panel(
                    mermaid_diagram,
                    title="[bold blue]Mermaid Sequence Diagram[/bold blue]",
                    border_style="blue",
                    expand=False,
                )
            )

    try:
        asyncio.run(run_trace())
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]An error occurred during trace execution:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="record")
def record_cmd(
    url: str = typer.Argument(..., help="Target URL to browse and record"),
    actions: str = typer.Argument(..., help="Comma-separated list of elements to click"),
) -> None:
    """Record a sequential clicking workflow as a video walkthrough."""
    async def run_record() -> None:
        from repollama.engines.browser import BrowserAgent
        from rich.panel import Panel
        import os

        # Parse actions
        actions_list = [a.strip() for a in actions.split(",") if a.strip()]
        
        video_dir = ".repollama_data/videos"
        os.makedirs(video_dir, exist_ok=True)
        
        console.print(f"[bold blue]Initializing browser recording...[/bold blue]")
        console.print(f"Target URL: {url}")
        console.print(f"Actions to execute: {actions_list}")
        
        async with BrowserAgent(record_video_dir=video_dir) as agent:
            try:
                await agent.navigate(url)
            except Exception as e:
                console.print(f"[bold red]Failed to navigate to {url}:[/bold red] {e}")
                raise typer.Exit(code=1)
                
            console.print("[bold blue]Executing workflow sequence...[/bold blue]")
            try:
                video_path = await agent.record_workflow(actions_list, output_filename="workflow.webm")
            except Exception as e:
                console.print(f"[bold red]Workflow execution or video generation failed:[/bold red] {e}")
                raise typer.Exit(code=1)
                
            actions_executed_str = "\n".join(f"  - {act}" for act in actions_list)
            console.print(
                Panel(
                    f"[bold green]✔ Workflow recording completed successfully![/bold green]\n\n"
                    f"[bold]Sequence of actions executed:[/bold]\n{actions_executed_str}\n\n"
                    f"[bold]Saved Video Walkthrough:[/bold]\n{video_path}",
                    title="[bold blue]Workflow Recorder[/bold blue]",
                    border_style="blue",
                    expand=False,
                )
            )

    try:
        asyncio.run(run_record())
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]An error occurred during recording execution:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="audit")
def audit_cmd() -> None:
    """Run an AI-driven multi-agent architecture and security audit on the codebase."""
    async def run_audit_flow() -> None:
        from repollama.llm.ollama import OllamaManager
        from repollama.agents.coordinator import AgentCoordinator
        from rich.panel import Panel
        
        ollama_mgr = OllamaManager(base_url=settings.OLLAMA_BASE_URL)
        
        # Verify Ollama is reachable
        is_up = await ollama_mgr.ping_server()
        if not is_up:
            console.print(
                f"[bold red]Error:[/bold red] Could not connect to local Ollama server at {settings.OLLAMA_BASE_URL}."
            )
            console.print("Please start Ollama and make sure it is running before running an audit.")
            raise typer.Exit(code=1)
            
        model = settings.DEFAULT_MODEL
        available_models = await ollama_mgr.list_models()
        if model not in available_models:
            matching_models = [m for m in available_models if m.startswith(model)]
            if matching_models:
                model = matching_models[0]
                console.print(f"[bold yellow]Warning:[/bold yellow] Exact model '{settings.DEFAULT_MODEL}' not found. Using matching installed model: '{model}'")
            else:
                console.print(f"[bold yellow]Warning:[/bold yellow] Default model '{settings.DEFAULT_MODEL}' was not found in your local Ollama instance.")
                console.print(f"Available models: {available_models}")
                console.print("We will attempt to proceed with the audit anyway, but it may fail if the model cannot be resolved.")
            
        # Create a mock context dictionary containing sample data
        mock_context = {
            "graph_stats": {
                "nodes": 150,
                "edges": 200,
            },
            "stack_info": {
                "language": "Python",
                "framework": "FastAPI",
                "dependencies": ["uvicorn", "pydantic", "fastapi"]
            },
            "secrets_warnings": [
                "Potential exposed API keys: secret_key missing in .env",
                "No database password set in config"
            ],
            "network_traffic": [
                {"url": "http://localhost:8000/api/v1/auth", "method": "POST", "status": 200}
            ]
        }
        
        coordinator = AgentCoordinator(ollama_manager=ollama_mgr, model=model)
        
        console.print("[bold blue]Starting Repository Audit Crew...[/bold blue]")
        
        # Use rich to print a spinner/status message
        with console.status("[bold green]Agents are analyzing the repository...[/bold green]") as status:
            try:
                results = await coordinator.run_audit(mock_context)
            except Exception as e:
                console.print()
                console.print(
                    Panel(
                        f"[bold red]✘ Audit Crew Failed![/bold red]\n\n"
                        f"An error occurred during multi-agent analysis:\n"
                        f"[yellow]{e}[/yellow]\n\n"
                        f"Please ensure Ollama is running and the model '{model}' is fully pulled.",
                        title="[bold red]Audit Error[/bold red]",
                        border_style="red",
                        expand=False,
                    )
                )
                raise typer.Exit(code=1)
                
        # Print results in Panels
        console.print()
        console.print(
            Panel(
                results["architecture"],
                title="[bold blue]Architecture Audit Report[/bold blue]",
                border_style="blue",
                expand=False,
            )
        )
        console.print()
        console.print(
            Panel(
                results["security"],
                title="[bold red]Security Audit Report[/bold red]",
                border_style="red",
                expand=False,
            )
        )

    try:
        asyncio.run(run_audit_flow())
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during the audit execution:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="debt")
def debt_cmd(
    repo_path: str = typer.Argument(".", help="Path to the target repository to evaluate technical debt"),
) -> None:
    """Analyze dependencies and git history to calculate and display a technical debt heatmap."""
    async def run_debt_flow() -> None:
        from pathlib import Path
        from repollama.engines.graph_builder import KnowledgeGraphBuilder
        from repollama.engines.debt_evaluator import DebtEvaluator
        from repollama.engines.git_miner import GitMiner, InvalidGitRepositoryError

        target_dir = Path(repo_path).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            console.print(
                f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{repo_path}[/yellow]"
            )
            raise typer.Exit(code=1)

        console.print(f"[bold blue]Evaluating technical debt for repository at:[/bold blue] {target_dir}")

        # 1. Run GitMiner to get file churn
        file_churn: dict[str, int] = {}
        try:
            miner = GitMiner(target_dir)
            file_churn = miner.get_file_churn(limit=99999)
        except Exception as e:
            console.print(
                f"[bold yellow]Warning:[/bold yellow] Git repository not detected or history unavailable: {e}. "
                "Defaulting churn metrics."
            )

        # 2. Run KnowledgeGraphBuilder and ASTParser to build the graph
        parser = ASTParser()
        graph_builder = KnowledgeGraphBuilder()

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

                # Populate the Knowledge Graph
                graph_builder.add_file_node(file_path_str, {"language": ast_meta.language})

                for cls in ast_meta.classes:
                    graph_builder.add_code_node(cls.name, "class", file_path_str)

                for func in ast_meta.functions:
                    graph_builder.add_code_node(func.name, "function", file_path_str)

                for imp in ast_meta.imports:
                    graph_builder.add_import_edge(file_path_str, imp)
            except Exception:
                pass

        # 3. Instantiate DebtEvaluator and call evaluate
        evaluator = DebtEvaluator(graph_builder.graph, file_churn)
        results = await evaluator.evaluate()

        if not results:
            console.print("[yellow]No supported files found to evaluate.[/yellow]")
            return

        # 4. Display Heatmap UI using Rich Table
        table = Table(title="Technical Debt Heatmap", show_header=True)
        table.add_column("File Path", style="cyan")
        table.add_column("Coupling", justify="right", style="magenta")
        table.add_column("Complexity", justify="right", style="magenta")
        table.add_column("Churn", justify="right", style="magenta")
        table.add_column("Debt Score", justify="right")
        table.add_column("Heatmap")

        for item in results:
            score = item["score"]
            coupling = item["coupling"]
            complexity = item["complexity"]
            churn = item["churn"]
            file_path = item["file"]

            num_blocks = int(round(score / 10))
            blocks = "█" * num_blocks

            if score > 80:
                style_str = "bold red"
            elif score > 50:
                style_str = "bold yellow"
            else:
                style_str = "bold green"

            table.add_row(
                file_path,
                str(coupling),
                str(complexity),
                str(churn),
                f"[{style_str}]{score}[/{style_str}]",
                f"[{style_str}]{blocks}[/{style_str}]",
            )

        console.print(table)

    try:
        asyncio.run(run_debt_flow())
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during debt evaluation:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="scan")
def scan_cmd(
    repo_path: str = typer.Argument(..., help="Path to the repository to scan"),
) -> None:
    """Scan the codebase for security threats and performance bottlenecks."""
    async def run_scan_flow() -> None:
        from pathlib import Path
        from repollama.engines.ast_parser import ASTParser
        from repollama.engines.security_auditor import SecurityAuditor
        from repollama.engines.performance_auditor import PerformanceAuditor

        target_dir = Path(repo_path).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            console.print(
                f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{repo_path}[/yellow]"
            )
            raise typer.Exit(code=1)

        console.print(f"[bold blue]Scanning repository for security and performance issues at:[/bold blue] {target_dir}")

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

        parser = ASTParser()
        file_contents: dict[str, str] = {}
        ast_data: list[dict[str, Any]] = []

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
                # Read content for secret scanning
                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                file_contents[file_path_str] = content

                # Parse AST
                ast_meta = parser.parse_file(path_obj)
                ast_dict = ast_meta.model_dump()
                ast_dict["file_path"] = file_path_str
                ast_data.append(ast_dict)
            except Exception:
                pass

        if not file_contents and not ast_data:
            console.print("[yellow]No supported files found to scan.[/yellow]")
            return

        # Run SecurityAuditor
        security_auditor = SecurityAuditor()
        secrets_flags = security_auditor.scan_secrets(file_contents)
        crypto_flags = security_auditor.scan_weak_crypto(ast_data)
        security_flags = secrets_flags + crypto_flags
        security_flags.sort(key=lambda x: (x.get("file", ""), x.get("line", 1), x.get("issue", "")))

        # Run PerformanceAuditor
        performance_auditor = PerformanceAuditor(file_contents=file_contents)
        performance_flags = performance_auditor.detect_anti_patterns(ast_data)
        performance_flags.sort(key=lambda x: (x.get("file", ""), x.get("target_function", ""), x.get("issue", "")))

        # Print Table 1: Security Threat Report
        # Columns: File, Issue, Severity, Line/Target
        sec_table = Table(title="Security Threat Report", show_header=True)
        sec_table.add_column("File", style="cyan")
        sec_table.add_column("Issue")
        sec_table.add_column("Severity")
        sec_table.add_column("Line/Target", justify="right")

        for flag in security_flags:
            file_val = flag.get("file", "")
            issue_val = flag.get("issue", "")
            sev_val = flag.get("severity", "")
            
            if sev_val.lower() == "high":
                sev_display = "[bold red]High[/bold red]"
            elif sev_val.lower() == "medium":
                sev_display = "[bold yellow]Medium[/bold yellow]"
            else:
                sev_display = sev_val

            line_val = flag.get("line")
            target_val = flag.get("target")
            line_target = str(line_val) if line_val is not None else (target_val or "")

            sec_table.add_row(file_val, issue_val, sev_display, line_target)

        # Print Table 2: Performance Bottlenecks
        # Columns: File, Issue, Severity, Target
        perf_table = Table(title="Performance Bottlenecks", show_header=True)
        perf_table.add_column("File", style="cyan")
        perf_table.add_column("Issue")
        perf_table.add_column("Severity")
        perf_table.add_column("Target")

        for flag in performance_flags:
            file_val = flag.get("file", "")
            issue_val = flag.get("issue", "")
            sev_val = flag.get("severity", "")

            if sev_val.lower() == "high":
                sev_display = "[bold red]High[/bold red]"
            elif sev_val.lower() == "medium":
                sev_display = "[bold yellow]Medium[/bold yellow]"
            else:
                sev_display = sev_val

            target_val = flag.get("target_function", "")

            perf_table.add_row(file_val, issue_val, sev_display, target_val)

        console.print()
        console.print(sec_table)
        console.print()
        console.print(perf_table)

    try:
        asyncio.run(run_scan_flow())
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during repository scan:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="drift")
def drift_cmd(
    repo_path: str = typer.Argument(".", help="Path to the Git repository"),
    base: str = typer.Option("HEAD~1", "--base", "-b", help="Base commit reference"),
    target: str = typer.Option("HEAD", "--target", "-t", help="Target commit reference or 'working_dir'"),
) -> None:
    """Compare imports/dependencies of Python/JS/TS files between two commits to detect architecture drift."""
    from pathlib import Path
    from repollama.engines.drift_engine import DriftDetector
    from rich.table import Table

    target_dir = Path(repo_path).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        console.print(
            f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{repo_path}[/yellow]"
        )
        raise typer.Exit(code=1)

    console.print(f"[bold blue]Detecting architecture drift for repository at:[/bold blue] {target_dir}")
    console.print(f"Comparing [yellow]{base}[/yellow] vs [yellow]{target}[/yellow]")

    try:
        detector = DriftDetector(target_dir)
        drift = detector.detect_drift(base_ref=base, target_ref=target)
    except Exception as e:
        console.print(f"[bold red]Error resolving references or running drift engine:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not drift:
        console.print("[bold green]Success: No architecture drift (added or removed dependencies) detected.[/bold green]")
        return

    # Use rich to print "Architecture Drift Report" table.
    table = Table(title="Architecture Drift Report", show_header=True)
    table.add_column("File", style="cyan")
    table.add_column("Added Dependencies (+)", no_wrap=True)
    table.add_column("Removed Dependencies (-)", no_wrap=True)

    for file_path, changes in drift.items():
        added_deps = changes.get("added", [])
        removed_deps = changes.get("removed", [])

        added_str = "\n".join(f"[bold red]+ {dep}[/bold red]" for dep in added_deps) if added_deps else ""
        removed_str = "\n".join(f"[bold green]- {dep}[/bold green]" for dep in removed_deps) if removed_deps else ""

        if added_deps or removed_deps:
            table.add_row(file_path, added_str, removed_str)

    console.print()
    console.print(table)
    console.print()


@app.command(name="docs")
def docs_cmd(
    repo_path: str = typer.Argument(..., help="Path to the repository to document"),
) -> None:
    """Generate system diagrams (C4, ERD) and a comprehensive repository wiki."""
    async def run_docs_flow() -> None:
        from pathlib import Path
        from repollama.engines.ast_parser import ASTParser
        from repollama.engines.diagram_generator import DiagramGenerator
        from repollama.engines.graph_builder import KnowledgeGraphBuilder
        from repollama.agents.documentation import DocumentationAgent
        from repollama.llm.ollama import OllamaManager

        target_dir = Path(repo_path).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            console.print(
                f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{repo_path}[/yellow]"
            )
            raise typer.Exit(code=1)

        # 1. Ensure the output directory .repollama_data/docs/ exists
        output_dir = Path(".repollama_data/docs").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"[bold blue]Scanning repository for system documentation at:[/bold blue] {target_dir}")

        parser = ASTParser()
        graph_builder = KnowledgeGraphBuilder()
        ast_classes: list[dict[str, Any]] = []
        total_files = 0
        detected_languages: set[str] = set()
        file_contents: dict[str, str] = {}
        ast_data: list[dict[str, Any]] = []

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

        with console.status("[bold green]Analyzing repository structure and AST...[/bold green]") as status:
            for path_obj in target_dir.rglob("*"):
                if not path_obj.is_file():
                    continue

                relative_path = path_obj.relative_to(target_dir)
                if any(part in exclude_dirs for part in relative_path.parts):
                    continue

                if path_obj.suffix.lower() not in supported_extensions:
                    continue

                file_path_str = str(relative_path)
                try:
                    # Read content for secret scanning and LLM context
                    with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    file_contents[file_path_str] = content

                    ast_meta = parser.parse_file(path_obj)
                    total_files += 1
                    detected_languages.add(ast_meta.language)

                    # Populate AST data for auditors
                    ast_dict = ast_meta.model_dump()
                    ast_dict["file_path"] = file_path_str
                    ast_data.append(ast_dict)

                    # Populate the Knowledge Graph builder to get realistic stats
                    graph_builder.add_file_node(file_path_str, {"language": ast_meta.language})

                    for cls in ast_meta.classes:
                        ast_classes.append({
                            "name": cls.name,
                            "start_line": cls.start_line,
                            "end_line": cls.end_line
                        })
                        graph_builder.add_code_node(cls.name, "class", file_path_str)

                    for func in ast_meta.functions:
                        graph_builder.add_code_node(func.name, "function", file_path_str)

                    for imp in ast_meta.imports:
                        graph_builder.add_import_edge(file_path_str, imp)

                except Exception as e:
                    # Non-fatal during AST parsing
                    console.print(f"[yellow]Warning:[/yellow] Failed to parse {file_path_str}: {e}")

        # Compute stats
        graph_stats = graph_builder.get_graph_stats()

        # Run security and performance audits to provide audit data
        audit_stats: dict[str, Any] = {}
        try:
            from repollama.engines.security_auditor import SecurityAuditor
            from repollama.engines.performance_auditor import PerformanceAuditor

            security_auditor = SecurityAuditor()
            secrets_flags = security_auditor.scan_secrets(file_contents)
            crypto_flags = security_auditor.scan_weak_crypto(ast_data)
            security_flags = secrets_flags + crypto_flags

            performance_auditor = PerformanceAuditor(file_contents=file_contents)
            performance_flags = performance_auditor.detect_anti_patterns(ast_data)

            audit_stats = {
                "total_security_issues": len(security_flags),
                "total_performance_issues": len(performance_flags),
                "security_issues": [
                    {
                        "file": flag.get("file"),
                        "line": flag.get("line"),
                        "issue": flag.get("issue"),
                        "severity": flag.get("severity")
                    } for flag in security_flags
                ],
                "performance_issues": [
                    {
                        "file": flag.get("file"),
                        "target_function": flag.get("target_function"),
                        "issue": flag.get("issue"),
                        "severity": flag.get("severity")
                    } for flag in performance_flags
                ]
            }
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Failed to run security/performance audits: {e}")

        # 2. Run DiagramGenerator and save files
        try:
            erd_str = DiagramGenerator.generate_erd(ast_classes)
            erd_path = output_dir / "ERD.md"
            with open(erd_path, "w", encoding="utf-8") as f:
                f.write(f"# Entity Relationship Diagram\n\n```mermaid\n{erd_str}\n```\n")
        except Exception as e:
            console.print(f"[bold red]Error generating ER Diagram:[/bold red] {e}")
            erd_path = None

        try:
            c4_str = DiagramGenerator.generate_c4_context(graph_stats)
            c4_path = output_dir / "C4.md"
            with open(c4_path, "w", encoding="utf-8") as f:
                f.write(f"# System Context Diagram\n\n```mermaid\n{c4_str}\n```\n")
        except Exception as e:
            console.print(f"[bold red]Error generating C4 Context Diagram:[/bold red] {e}")
            c4_path = None

        # 3. Instantiate DocumentationAgent and generate WIKI.md
        wiki_path = output_dir / "WIKI.md"
        wiki_saved = False

        ollama_mgr = OllamaManager(base_url=settings.OLLAMA_BASE_URL)
        is_up = await ollama_mgr.ping_server()
        if not is_up:
            console.print(
                "[bold yellow]Warning:[/bold yellow] Could not connect to local Ollama server during WIKI generation. "
                "Diagrams were saved, but WIKI.md generation was skipped."
            )
        else:
            model = settings.DEFAULT_MODEL
            try:
                available_models = await ollama_mgr.list_models()
                if model not in available_models:
                    matching_models = [m for m in available_models if m.startswith(model)]
                    if matching_models:
                        model = matching_models[0]
                    else:
                        console.print(f"[bold yellow]Warning:[/bold yellow] Model '{settings.DEFAULT_MODEL}' not found. Attempting generation anyway.")

                mock_context = {
                    "repo_stats": {
                        "repo_name": target_dir.name,
                        "total_files": total_files,
                        "total_classes": len(ast_classes),
                        "graph_nodes": graph_stats.get("node_count", 0),
                        "graph_edges": graph_stats.get("edge_count", 0),
                        "detected_languages": list(detected_languages),
                    },
                    "audit_stats": audit_stats
                }

                agent = DocumentationAgent(ollama_manager=ollama_mgr, model=model)
                with console.status("[bold green]Generating wiki documentation via Ollama...[/bold green]") as status:
                    wiki_text = await agent.analyze(mock_context)

                with open(wiki_path, "w", encoding="utf-8") as f:
                    f.write(wiki_text)
                wiki_saved = True
            except Exception as e:
                console.print(
                    f"[bold yellow]Warning:[/bold yellow] Graceful recovery: LLM Wiki generation failed or timed out: {e}. "
                    "Mermaid diagrams are still successfully saved."
                )

        # 4. Success Panel showing paths
        success_lines = [
            "[bold green]✔ Developer Portal Artifacts Successfully Generated![/bold green]",
            "",
        ]
        if erd_path:
            success_lines.append(f"  [bold blue]ERD Diagram:[/bold blue] {erd_path.absolute()}")
        if c4_path:
            success_lines.append(f"  [bold blue]C4 Diagram:[/bold blue]  {c4_path.absolute()}")
        if wiki_saved:
            success_lines.append(f"  [bold blue]Wiki Doc:[/bold blue]     {wiki_path.absolute()}")
        else:
            success_lines.append("  [bold yellow]Wiki Doc:[/bold yellow]     (Skipped/Failed - Check warnings above)")

        console.print(
            Panel(
                "\n".join(success_lines),
                title="[bold green]Success[/bold green]",
                border_style="green",
                expand=False,
            )
        )

    try:
        asyncio.run(run_docs_flow())
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during documentation generation:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="watch")
def watch_cmd(
    repo_path: str = typer.Argument(".", help="Path to the target repository to watch"),
) -> None:
    """Monitor the file system for live code changes, triggering incremental updates."""
    from pathlib import Path
    import threading
    import time
    from repollama.engines.graph_builder import KnowledgeGraphBuilder
    from repollama.engines.watcher import RepoWatcher
    from repollama.engines.cache_manager import CacheManager

    target_dir = Path(repo_path).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        console.print(
            f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{repo_path}[/yellow]"
        )
        raise typer.Exit(code=1)

    console.print(
        f"👀 Repollama Daemon watching for changes in [yellow]{target_dir}[/yellow]... (Press Ctrl+C to stop)"
    )

    # Initialize parser and graph builder
    parser = ASTParser()
    graph_builder = KnowledgeGraphBuilder()
    cache_mgr = CacheManager(target_dir)
    hash_cache = cache_mgr.load_cache()

    # Perform a quick initial index of the repo to populate the graph and the hash_cache
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

    console.print("[bold blue]Populating initial Knowledge Graph and cache...[/bold blue]")
    for path_obj in target_dir.rglob("*"):
        if not path_obj.is_file():
            continue

        relative_path = path_obj.relative_to(target_dir)
        if any(part in exclude_dirs for part in relative_path.parts):
            continue

        if path_obj.suffix.lower() not in supported_extensions:
            continue

        file_key = str(relative_path)
        try:
            ast_meta = parser.parse_file(path_obj)
            graph_builder.add_file_node(file_key, {"language": ast_meta.language})

            for cls in ast_meta.classes:
                graph_builder.add_code_node(cls.name, "class", file_key)

            for func in ast_meta.functions:
                graph_builder.add_code_node(func.name, "function", file_key)

            for imp in ast_meta.imports:
                graph_builder.add_import_edge(file_key, imp)

            h = cache_mgr.compute_hash(str(path_obj))
            if h is not None:
                hash_cache[file_key] = h
        except Exception:
            pass

    cache_mgr.save_cache(hash_cache)
    stats = graph_builder.get_graph_stats()
    console.print(
        f"[bold green]✓ Initial index complete. Graph contains {stats['node_count']} nodes and {stats['edge_count']} edges.[/bold green]"
    )

    lock = threading.Lock()

    def on_file_changed(file_path: str, event_type: str) -> None:
        with lock:
            # Get relative path for logging and graph keys
            try:
                rel_path = Path(file_path).relative_to(target_dir)
            except ValueError:
                rel_path = Path(file_path)
            file_key = str(rel_path)

            # Check if file actually changed
            if not cache_mgr.has_changed(file_path, hash_cache):
                return

            time_str = time.strftime("%H:%M:%S")

            # Print lightning bolt message: [14:32:01] ⚡ Change detected in src/main.py. Patching graph...
            console.print(f"[{time_str}] ⚡ Change detected in {file_key}. Patching graph...")

            # Call KnowledgeGraphBuilder.remove_file_subgraph
            graph_builder.remove_file_subgraph(file_key)

            # If the file still exists (not deleted), parse it and add it back
            p = Path(file_path)
            if p.exists() and p.is_file():
                try:
                    ast_meta = parser.parse_file(p)
                    # Add nodes/edges back
                    graph_builder.add_file_node(file_key, {"language": ast_meta.language})
                    for cls in ast_meta.classes:
                        graph_builder.add_code_node(cls.name, "class", file_key)
                    for func in ast_meta.functions:
                        graph_builder.add_code_node(func.name, "function", file_key)
                    for imp in ast_meta.imports:
                        graph_builder.add_import_edge(file_key, imp)
                except Exception as e:
                    console.print(f"[{time_str}] ⚠️ Failed to parse {file_key}: {e}")

            # Save the updated hash cache to disk
            cache_mgr.save_cache(hash_cache)

    watcher = RepoWatcher(target_dir, on_file_changed)
    watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Stopping Repollama Daemon...[/bold yellow]")
    finally:
        watcher.stop()
        console.print("[bold green]Stopped.[/bold green]")



@app.command(name="macro")
def macro_cmd(
    repo_paths: list[str] = typer.Argument(..., help="Paths to the repositories to ingest and merge"),
) -> None:
    """Ingest multiple repositories, merge their knowledge graphs, and generate cross-repo architecture diagrams."""
    from pathlib import Path
    from repollama.engines.macro_compiler import MacroCompiler
    from repollama.engines.diagram_generator import DiagramGenerator

    # Validate paths first
    valid_paths = []
    for path in repo_paths:
        p = Path(path).resolve()
        if not p.exists() or not p.is_dir():
            console.print(
                f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{path}[/yellow]"
            )
            raise typer.Exit(code=1)
        valid_paths.append(str(p))

    # Ensure output directory exists (relative to current working directory)
    output_dir = Path(".repollama_data/docs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with console.status("[bold green]Compiling macro repository structures...[/bold green]"):
        compiler = MacroCompiler()
        # Compile
        macro_graph = compiler.compile(valid_paths)
        # Resolve links
        compiler.resolve_cross_links()
        # Generate macro C4 diagram
        macro_c4 = DiagramGenerator.generate_macro_c4(macro_graph)

    # Save to MACRO_C4.md
    macro_c4_path = output_dir / "MACRO_C4.md"
    try:
        with open(macro_c4_path, "w", encoding="utf-8") as f:
            f.write(f"# Macro Architecture Diagram\n\n```mermaid\n{macro_c4}\n```\n")
    except Exception as e:
        console.print(f"[bold red]Error saving Macro C4 Diagram:[/bold red] {e}")
        raise typer.Exit(code=1)

    # Print success panel
    success_lines = [
        f"[bold green]✔ Macro Compiler merged {len(repo_paths)} repositories successfully![/bold green]",
        "",
        f"  [bold blue]Repositories Merged:[/bold blue]  {len(repo_paths)}",
        f"  [bold blue]Macro Graph Nodes:[/bold blue]    {macro_graph.number_of_nodes()}",
        f"  [bold blue]Macro Graph Edges:[/bold blue]    {macro_graph.number_of_edges()}",
        f"  [bold blue]Output Diagram Path:[/bold blue]  {macro_c4_path.absolute()}",
    ]
    console.print(
        Panel(
            "\n".join(success_lines),
            title="[bold green]Success[/bold green]",
            border_style="green",
            expand=False,
        )
    )


@app.command(name="ci-check")
def ci_check_cmd(
    repo_path: str = typer.Argument(".", help="Path to the repository to check"),
    base: str = typer.Option("HEAD~1", "--base", "-b", help="Base commit reference"),
    target: str = typer.Option("HEAD", "--target", "-t", help="Target commit reference"),
    role: str = typer.Option("developer", "--role", "-r", help="User role for bypass check"),
) -> None:
    """Evaluate PR for architectural drift and technical debt, acting as a CI/CD quality gate."""
    import sys
    from pathlib import Path
    from repollama.engines.ci_gatekeeper import CIGatekeeper
    from repollama.core.enterprise import AuditLogger, RBACManager
    from rich.panel import Panel
    from rich.table import Table

    # Log action using AuditLogger
    try:
        logger = AuditLogger()
        logger.log_action("CI Check Triggered by User")
    except Exception as e:
        console.print(f"[bold yellow]Warning:[/bold yellow] Failed to write to audit log: {e}")

    async def run():
        target_dir = Path(repo_path).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            console.print(
                f"[bold red]Error:[/bold red] Target directory does not exist or is not a directory: [yellow]{repo_path}[/yellow]"
            )
            sys.exit(1)

        gatekeeper = CIGatekeeper()
        try:
            report = await gatekeeper.evaluate_pr(target_dir, base, target)
        except Exception as e:
            console.print(f"[bold red]Error evaluating PR quality gate:[/bold red] {e}")
            sys.exit(1)

        passed = report["passed"]
        drift_report = report["drift"]
        highest_debt_score = report["highest_debt_score"]

        # Check for any added dependencies
        has_drift = False
        for changes in drift_report.values():
            if changes.get("added"):
                has_drift = True
                break

        # Check RBAC bypass logic
        rbac = RBACManager()
        bypassed = False
        if has_drift and rbac.has_permission(role, "bypass_drift"):
            bypassed = True
            # If bypassed, then drift does not cause gatekeeper failure
            # If high debt is also present, it still fails.
            passed = (highest_debt_score <= 80)

        # Build Pass/Fail Panel
        if passed:
            status_text = "[bold green]✔ PASS[/bold green]"
            if bypassed:
                status_text += " [yellow](Bypassed Drift Check via Architect role)[/yellow]"
            border_style = "green"
            message = "PR meets all architectural and quality standard gates."
        else:
            status_text = "[bold red]✘ FAIL[/bold red]"
            border_style = "red"
            message = "PR failed one or more quality gate thresholds."

        panel_lines = [
            f"Status: {status_text}",
            message,
            "",
            f"  [bold blue]Highest Debt Score:[/bold blue] {highest_debt_score} / 80",
            f"  [bold blue]Architectural Drift (Added Deps):[/bold blue] {'Yes' if has_drift else 'No'}",
        ]

        if has_drift:
            panel_lines.append(f"  [bold blue]Bypassed Drift Check:[/bold blue] {'Yes' if bypassed else 'No'}")

        console.print()
        console.print(
            Panel(
                "\n".join(panel_lines),
                title="[bold]Repollama CI/CD Governance Gate[/bold]",
                border_style=border_style,
                expand=False,
            )
        )
        console.print()

        # If there's architectural drift, display the detailed drift table
        if drift_report:
            table = Table(title="Drift Details", show_header=True)
            table.add_column("File", style="cyan")
            table.add_column("Added Dependencies (+)", no_wrap=True)
            table.add_column("Removed Dependencies (-)", no_wrap=True)

            for file_path, changes in drift_report.items():
                added_deps = changes.get("added", [])
                removed_deps = changes.get("removed", [])
                if added_deps or removed_deps:
                    added_str = "\n".join(f"[bold red]+ {dep}[/bold red]" for dep in added_deps) if added_deps else ""
                    removed_str = "\n".join(f"[bold green]- {dep}[/bold green]" for dep in removed_deps) if removed_deps else ""
                    table.add_row(file_path, added_str, removed_str)
            console.print(table)
            console.print()

        if passed:
            sys.exit(0)
        else:
            sys.exit(1)

    try:
        asyncio.run(run())
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        console.print(f"[bold red]Unexpected error in ci-check command:[/bold red] {e}")
        sys.exit(1)


@app.command(name="init-ci")
def init_ci_cmd() -> None:
    """Initialize a standard GitHub Actions workflow configuration for Repollama CI governance."""
    from pathlib import Path
    
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    workflow_file = workflow_dir / "repollama_gate.yml"
    
    yaml_content = """name: Repollama CI Gate

on:
  pull_request:
    branches: [ main, master ]

jobs:
  repollama-gate:
    name: Repollama Quality & Architecture Gate
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Fetch all history for diff/drift check

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Python Dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f pyproject.toml ]; then pip install .; fi
          # Ensure repollama CLI is installed/available
          pip install git+https://github.com/vanshjain99/Repollama.git || true

      - name: Run Repollama CI Check
        run: |
          # Run the quality gate check comparing base commit to target PR head
          repollama ci-check . --base ${{ github.event.pull_request.base.sha }} --target ${{ github.event.pull_request.head.sha }}
"""
    try:
        with open(workflow_file, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        console.print(
            Panel(
                f"[bold green]✔ Successfully initialized GitHub Actions workflow![/bold green]\n\n"
                f"Workflow config file written to: [cyan]{workflow_file}[/cyan]\n"
                f"Make sure you push this file to trigger the quality gate on pull requests.",
                title="[bold green]Success[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except Exception as e:
        console.print(f"[bold red]Error writing workflow file:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


