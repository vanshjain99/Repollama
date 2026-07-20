from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any, Optional
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from repollama.core.config import settings
from repollama.llm.ollama import OllamaManager
from repollama.engines.ast_parser import ASTParser
from repollama.engines.graph_builder import KnowledgeGraphBuilder
from repollama.database.vector_store import LocalVectorStore

# Initialize the FastAPI application
app = FastAPI(
    title="Repollama API",
    description="Autonomous Software Intelligence Engine Headless Core",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — permissive for local-first Tauri desktop app. All Tauri origins plus
# the Vite dev server are explicitly listed; wildcard ensures nothing is missed.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
        "https://tauri.localhost",
        "http://tauri.localhost",
        "asset://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize the connection manager
ollama_manager = OllamaManager(base_url=settings.OLLAMA_BASE_URL)


@app.get("/api/v1/health")
@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Check the health status of the API, Docker daemon, and local Ollama service.

    Returns:
        A dictionary containing boolean statuses for backend, docker, and ollama.
    """
    ollama_reachable = await ollama_manager.ping_server()

    docker_reachable = False
    try:
        import docker
        client = docker.from_env()
        client.ping()
        docker_reachable = True
    except Exception:
        docker_reachable = False

    return {
        "status": "healthy",
        "backend": True,
        "docker": docker_reachable,
        "ollama": ollama_reachable,
    }



@app.get("/api/v1/analyze/stream")
async def analyze_stream(path: str = Query(..., description="Path to the repository to index")) -> EventSourceResponse:
    """Orchestrate codebase analysis and yield live logs using Server-Sent Events (SSE)."""
    async def event_generator():
        target_dir = Path(path).resolve()
        yield {"data": f"[System] Target workspace set to {target_dir}"}

        if not target_dir.exists() or not target_dir.is_dir():
            yield {"data": f"[System] Error: Target workspace does not exist or is not a directory: {target_dir}"}
            yield {"data": "[Pipeline] Analysis Complete!"}
            return

        try:
            parser = ASTParser()
            graph_builder = KnowledgeGraphBuilder()
            vector_store = LocalVectorStore()
        except Exception as e:
            yield {"data": f"[System] Error initializing analysis engines: {e}"}
            yield {"data": "[Pipeline] Analysis Complete!"}
            return

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

        # Traverse directory
        for path_obj in target_dir.rglob("*"):
            # Yield control back to event loop to keep the server responsive
            await asyncio.sleep(0.001)

            if not path_obj.is_file():
                continue

            relative_path = path_obj.relative_to(target_dir)
            if any(part in exclude_dirs for part in relative_path.parts):
                continue

            if path_obj.suffix.lower() not in supported_extensions:
                continue

            file_path_str = str(relative_path)
            yield {"data": f"[AST] Parsing {file_path_str}..."}

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

                # Populate the Vector Store
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
                    repo_path=str(target_dir),
                )
                indexed_files_count += 1
            except Exception as e:
                yield {"data": f"[System] Warning: Failed to index {file_path_str}: {e}"}

        # Retrieve completion stats
        try:
            graph_stats = graph_builder.get_graph_stats()
            node_count = graph_stats.get("node_count", 0)
            edge_count = graph_stats.get("edge_count", 0)
        except Exception:
            node_count = 0
            edge_count = 0

        try:
            vs_size = vector_store.collection.count()
        except Exception:
            vs_size = 0

        # Query GitMiner for commits count if it's a valid Git repo
        commit_count = 0
        try:
            from repollama.engines.git_miner import GitMiner
            miner = GitMiner(target_dir)
            meta = miner.get_repository_metadata()
            commit_count = meta.get("commit_count", 0)
        except Exception:
            commit_count = 0

        yield {
            "data": (
                f"[System] Analysis complete. Nodes: {node_count}, "
                f"Edges: {edge_count}, Collection Size: {vs_size}, "
                f"Commits: {commit_count}"
            )
        }

        # Serialize and save the graph
        try:
            import json
            import os
            from networkx.readwrite import json_graph
            graph_data = json_graph.node_link_data(graph_builder.graph)
            os.makedirs(".repollama_data", exist_ok=True)
            with open(".repollama_data/graph.json", "w") as f:
                json.dump(graph_data, f)
        except Exception as e:
            yield {"data": f"[System] Warning: Failed to save graph: {e}"}

        yield {"data": "[Pipeline] Analysis Complete!"}

    return EventSourceResponse(event_generator())


from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    path: Optional[str] = None
    repo_paths: Optional[list[str]] = None


@app.post("/api/v1/analyze")
async def trigger_analyze(request: AnalyzeRequest) -> dict[str, Any]:
    """Trigger repository analysis using MacroCompiler."""
    from repollama.engines.macro_compiler import MacroCompiler

    paths = request.repo_paths or ([request.path] if request.path else [])
    if not paths:
        return {"status": "error", "message": "No repository path provided"}

    try:
        compiler = MacroCompiler()
        graph = compiler.compile(paths)
        compiler.resolve_cross_links()
        return {
            "status": "success",
            "message": "Macro compilation complete",
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


class ChatRequest(BaseModel):
    message: str
    model: str = "qwen2.5-coder:1.5b"
    ollama_endpoint: Optional[str] = None  # Optional per-request Ollama URL override
    repo_path: str = ""  # Active repository path for RAG context isolation


@app.get("/api/v1/graph")
async def get_graph() -> dict[str, Any]:
    """Retrieve the serialized knowledge graph nodes and edges.

    Searches multiple candidate paths for the graph data file so that the
    server can be started from any working directory.
    """
    import json

    # Candidate locations — relative CWD first, then next to this source file
    candidates = [
        Path(".repollama_data/graph.json"),
        Path(".repollama_data") / "graph.json",
        Path(__file__).parent.parent / ".repollama_data" / "graph.json",
        Path(__file__).parent.parent.parent / ".repollama_data" / "graph.json",
    ]

    for graph_path in candidates:
        if graph_path.exists():
            try:
                with open(graph_path) as f:
                    data = json.load(f)
                # Normalise NetworkX node-link format
                nodes = data.get("nodes", [])
                links = data.get("links", data.get("edges", []))
                return {"nodes": nodes, "links": links, "source_path": str(graph_path)}
            except Exception as exc:
                return {"nodes": [], "links": [], "error": str(exc)}

    return {"nodes": [], "links": [], "error": "Graph data not found. Run analysis first."}


@app.post("/api/v1/chat")
async def chat(request: ChatRequest, http_request: Request) -> dict[str, Any]:
    """Chat with the codebase using local Ollama and ChromaDB context (RAG).

    The Ollama endpoint can be overridden per-request via:
    - The ``ollama_endpoint`` field in the JSON body, or
    - The ``X-Ollama-Endpoint`` HTTP header.
    This allows the frontend Settings panel to dynamically reroute without
    requiring a server restart.
    """
    try:
        # Resolve the active Ollama URL (per-request override > stored setting)
        endpoint_override = (
            request.ollama_endpoint
            or http_request.headers.get("X-Ollama-Endpoint")
        )
        if endpoint_override and endpoint_override.strip():
            active_manager = OllamaManager(base_url=endpoint_override.strip())
        else:
            active_manager = ollama_manager

        vector_store = LocalVectorStore()
        # Query similar documents scoped to the active repository
        results = vector_store.query_similar(
            request.message,
            n_results=5,
            repo_path=request.repo_path,
        )

        context_parts: list[str] = []
        for r in results:
            file_path = r["metadata"].get("file_path", r["id"])
            lang = r["metadata"].get("language", "")
            content = r["document"]
            context_parts.append(f"--- File: {file_path} ({lang}) ---\n{content}")

        context_str = "\n\n".join(context_parts)

        prompt = (
            "You are Repollama Code Companion, an offline software intelligence assistant.\n"
            "Use the following codebase context retrieved from the local index to answer the user's question.\n"
            "If the context does not contain enough information, use your general knowledge of the stack "
            "but mention that it is outside the local index.\n\n"
            "--- Codebase Context ---\n"
            f"{context_str}\n"
            "------------------------\n\n"
            f"Question: {request.message}\n\n"
            "Answer:"
        )

        response_text = await active_manager.generate(prompt, request.model)
        return {"response": response_text, "model": request.model, "endpoint": active_manager.base_url}
    except Exception as e:
        return {"response": f"Error generating response from local LLM: {str(e)}", "error": True}


@app.get("/api/v1/settings")
async def get_settings() -> dict[str, Any]:
    """Get dynamic backend settings."""
    return {
        "ollama_base_url": ollama_manager.base_url,
        "default_model": settings.DEFAULT_MODEL,
    }


@app.post("/api/v1/settings")
async def update_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Update dynamic backend settings in memory."""
    if "ollama_base_url" in data:
        ollama_manager.base_url = data["ollama_base_url"].rstrip("/")
    return {
        "status": "success",
        "settings": {
            "ollama_base_url": ollama_manager.base_url,
            "default_model": settings.DEFAULT_MODEL,
        }
    }


# ---------------------------------------------------------------------------
# Sandbox Endpoints
# ---------------------------------------------------------------------------

class SandboxStartRequest(BaseModel):
    path: Optional[str] = None


class SandboxStopRequest(BaseModel):
    container_id: Optional[str] = None


active_sandbox_info: dict[str, Any] = {
    "status": "stopped",
    "container_id": None,
    "host_port": None,
    "stack": None,
    "language": None,
    "warnings": [],
}


@app.get("/api/v1/sandbox/status")
async def get_sandbox_status() -> dict[str, Any]:
    """Get active Docker sandbox status and configuration."""
    from repollama.engines.sandbox import DockerSandbox
    sandbox = DockerSandbox()
    return {
        "docker_available": sandbox.is_available,
        **active_sandbox_info
    }


@app.post("/api/v1/sandbox/start")
async def start_sandbox(request: SandboxStartRequest = SandboxStartRequest()) -> dict[str, Any]:
    """Boot a Docker sandbox container for the specified repository."""
    from repollama.engines.sandbox import EnvironmentDetector, DockerSandbox
    repo_path = request.path or "."
    detector = EnvironmentDetector(repo_path)
    stack_info = detector.detect_stack()
    secrets_info = detector.detect_secrets()
    warnings = []
    if "warning" in secrets_info:
        warnings.append(secrets_info["warning"])

    sandbox = DockerSandbox()
    if not sandbox.is_available:
        return {
            "status": "error",
            "message": "Docker daemon is not running or available on host system.",
            "docker_available": False,
            "stack_info": stack_info,
            "warnings": warnings,
        }

    try:
        res = sandbox.start_sandbox(repo_path, stack_info)
        active_sandbox_info.update({
            "status": "running",
            "container_id": res.get("container_id"),
            "host_port": res.get("host_port"),
            "stack": stack_info.get("stack"),
            "language": stack_info.get("language"),
            "warnings": warnings,
        })
        return {
            "status": "success",
            "message": "Sandbox container booted successfully",
            "container_id": res.get("container_id"),
            "host_port": res.get("host_port"),
            "stack_info": stack_info,
            "warnings": warnings,
        }
    except Exception as e:
        active_sandbox_info["status"] = "error"
        return {
            "status": "error",
            "message": str(e),
            "docker_available": sandbox.is_available,
            "stack_info": stack_info,
            "warnings": warnings,
        }


@app.post("/api/v1/sandbox/stop")
async def stop_sandbox(request: SandboxStopRequest = SandboxStopRequest()) -> dict[str, Any]:
    """Shut down and remove an active Docker sandbox container."""
    from repollama.engines.sandbox import DockerSandbox
    container_id = request.container_id or active_sandbox_info.get("container_id")
    if not container_id:
        active_sandbox_info.update({
            "status": "stopped",
            "container_id": None,
            "host_port": None,
        })
        return {"status": "success", "message": "No sandbox container active"}

    try:
        sandbox = DockerSandbox()
        sandbox.stop_sandbox(container_id)
        active_sandbox_info.update({
            "status": "stopped",
            "container_id": None,
            "host_port": None,
        })
        return {"status": "success", "message": "Sandbox container shut down successfully"}
    except Exception as e:
        active_sandbox_info.update({
            "status": "stopped",
            "container_id": None,
            "host_port": None,
        })
        return {"status": "success", "message": f"Container stopped: {str(e)}"}


# ---------------------------------------------------------------------------
# Workflow & Sequence Diagram Endpoints
# ---------------------------------------------------------------------------

class WorkflowTraceRequest(BaseModel):
    url: str = "http://localhost:8000"
    action: str = "Login"


@app.get("/api/v1/workflows")
async def list_workflows() -> dict[str, Any]:
    """Return available workflow sequence diagrams."""
    default_workflows = [
        {
            "id": "login-workflow",
            "title": "Login Workflow",
            "description": "User authentication flow with POST /api/v1/login and profile retrieval.",
            "diagram": (
                "sequenceDiagram\n"
                "    actor User\n"
                "    participant Browser\n"
                "    participant Backend\n"
                '    User->>Browser: Clicks "Login"\n'
                "    Browser->>Backend: POST /api/v1/login\n"
                "    Backend-->>Browser: 200 (JWT Token)\n"
                "    Browser->>Backend: GET /api/v1/user/profile\n"
                "    Backend-->>Browser: 200 (Profile Data)"
            )
        },
        {
            "id": "search-workflow",
            "title": "Repository Search & RAG Workflow",
            "description": "Natural language query submission and vector search retrieval.",
            "diagram": (
                "sequenceDiagram\n"
                "    actor User\n"
                "    participant Browser\n"
                "    participant Backend\n"
                "    participant VectorStore\n"
                '    User->>Browser: Clicks "Search Codebase"\n'
                "    Browser->>Backend: POST /api/v1/chat\n"
                "    Backend->>VectorStore: query_similar(n_results=5)\n"
                "    VectorStore-->>Backend: Top Relevant AST Nodes\n"
                "    Backend-->>Browser: 200 (RAG Response)"
            )
        },
        {
            "id": "ingest-workflow",
            "title": "Repository Ingestion SSE Workflow",
            "description": "Live log streaming during Tree-sitter parsing and graph building.",
            "diagram": (
                "sequenceDiagram\n"
                "    actor User\n"
                "    participant Browser\n"
                "    participant Backend\n"
                '    User->>Browser: Clicks "Start Analysis"\n'
                "    Browser->>Backend: GET /api/v1/analyze/stream\n"
                "    Backend-->>Browser: SSE Log: [AST] Parsing files...\n"
                "    Backend-->>Browser: SSE Log: [Graph] Building NetworkX nodes...\n"
                "    Backend-->>Browser: SSE Log: [Pipeline] Analysis Complete!"
            )
        },
        {
            "id": "sandbox-workflow",
            "title": "Docker Sandbox Lifecycle Workflow",
            "description": "Stack detection, secret validation, and Docker container startup.",
            "diagram": (
                "sequenceDiagram\n"
                "    actor User\n"
                "    participant Browser\n"
                "    participant Backend\n"
                "    participant DockerDaemon\n"
                '    User->>Browser: Clicks "Boot Sandbox"\n'
                "    Browser->>Backend: POST /api/v1/sandbox/start\n"
                "    Backend->>DockerDaemon: run(node:20-alpine)\n"
                "    DockerDaemon-->>Backend: Container ID & Mapped Port\n"
                "    Backend-->>Browser: 200 (Running on host port 5173)"
            )
        }
    ]
    return {"workflows": default_workflows}


@app.post("/api/v1/workflows/trace")
async def trace_workflow(request: WorkflowTraceRequest) -> dict[str, Any]:
    """Trace a browser action dynamically and return a generated sequence diagram."""
    from repollama.engines.browser import BrowserAgent
    from repollama.engines.sequence_builder import SequenceDiagramBuilder

    try:
        async with BrowserAgent() as agent:
            await agent.navigate(request.url)
            result = await agent.click_and_trace(request.action)
            diagram = SequenceDiagramBuilder.generate(result["action"], result["traffic"])
            return {
                "status": "success",
                "action": request.action,
                "url": request.url,
                "traffic": result["traffic"],
                "diagram": diagram,
            }
    except Exception as e:
        fallback_traffic = [
            {"url": f"{request.url}/api/v1/action", "method": "POST", "status": 200}
        ]
        diagram = SequenceDiagramBuilder.generate(request.action, fallback_traffic)
        return {
            "status": "warning",
            "message": f"Browser trace note: {str(e)}. Generated default sequence diagram.",
            "action": request.action,
            "url": request.url,
            "traffic": fallback_traffic,
            "diagram": diagram,
        }


# ---------------------------------------------------------------------------
# Engineering Intelligence & Audit Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/intelligence/debt")
async def get_debt_report(path: Optional[str] = Query(None, description="Path to repo")) -> dict[str, Any]:
    """Evaluate technical debt across repository files."""
    import json
    import networkx as nx
    from networkx.readwrite import json_graph
    from repollama.engines.debt_evaluator import DebtEvaluator
    from repollama.engines.git_miner import GitMiner
    
    target_dir = Path(path).resolve() if path else Path.cwd()
    
    graph = nx.DiGraph()
    candidates = [
        Path(".repollama_data/graph.json"),
        Path(__file__).parent.parent / ".repollama_data" / "graph.json",
        target_dir / ".repollama_data" / "graph.json",
    ]
    for g_path in candidates:
        if g_path.exists():
            try:
                with open(g_path) as f:
                    data = json.load(f)
                graph = json_graph.node_link_graph(data)
                break
            except Exception:
                pass

    if len(graph.nodes) == 0:
        from repollama.engines.ast_parser import ASTParser
        from repollama.engines.graph_builder import KnowledgeGraphBuilder
        parser = ASTParser()
        builder = KnowledgeGraphBuilder()
        exclude = {".git", "node_modules", "venv", ".venv", "__pycache__", ".repollama_data", "dist", "build"}
        if target_dir.exists() and target_dir.is_dir():
            for p in target_dir.rglob("*"):
                if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                    rel = p.relative_to(target_dir)
                    if any(part in exclude for part in rel.parts):
                        continue
                    try:
                        ast_meta = parser.parse_file(p)
                        file_str = str(rel)
                        builder.add_file_node(file_str, {"language": ast_meta.language})
                        for cls in ast_meta.classes:
                            builder.add_code_node(cls.name, "class", file_str)
                        for func in ast_meta.functions:
                            builder.add_code_node(func.name, "function", file_str)
                        for imp in ast_meta.imports:
                            builder.add_import_edge(file_str, imp)
                    except Exception:
                        pass
        graph = builder.graph

    churn_dict: dict[str, int] = {}
    try:
        if target_dir.exists() and (target_dir / ".git").exists():
            miner = GitMiner(target_dir)
            churn_dict = miner.get_file_churn()
    except Exception:
        pass

    evaluator = DebtEvaluator(graph, churn_dict)
    results = await evaluator.evaluate()
    return {"status": "success", "results": results, "count": len(results)}


@app.get("/api/v1/intelligence/audits")
async def get_audit_reports(path: Optional[str] = Query(None, description="Path to repo")) -> dict[str, Any]:
    """Run security and performance auditors on codebase."""
    from repollama.engines.ast_parser import ASTParser
    from repollama.engines.security_auditor import SecurityAuditor
    from repollama.engines.performance_auditor import PerformanceAuditor

    target_dir = Path(path).resolve() if path else Path.cwd()
    exclude = {".git", "node_modules", "venv", ".venv", "__pycache__", ".repollama_data", "dist", "build"}
    
    file_contents: dict[str, str] = {}
    ast_data_list: list[dict[str, Any]] = []
    parser = ASTParser()

    if target_dir.exists() and target_dir.is_dir():
        for p in target_dir.rglob("*"):
            if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                rel = str(p.relative_to(target_dir))
                if any(part in exclude for part in Path(rel).parts):
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    file_contents[rel] = text
                    ast_meta = parser.parse_file(p)
                    ast_data_list.append({
                        "file_path": rel,
                        "language": ast_meta.language,
                        "imports": ast_meta.imports,
                        "classes": [{"name": c.name, "start_line": c.start_line} for c in ast_meta.classes],
                        "functions": [{"name": f.name, "start_line": f.start_line, "end_line": f.end_line} for f in ast_meta.functions],
                    })
                except Exception:
                    pass

    sec_auditor = SecurityAuditor()
    sec_secrets = sec_auditor.scan_secrets(file_contents)
    sec_crypto = sec_auditor.scan_weak_crypto(ast_data_list)
    security_flags = sec_secrets + sec_crypto

    perf_auditor = PerformanceAuditor(file_contents)
    performance_flags = perf_auditor.detect_anti_patterns(ast_data_list)

    return {
        "status": "success",
        "security": security_flags,
        "performance": performance_flags,
    }


# ---------------------------------------------------------------------------
# Video Gallery & Streaming Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/videos")
async def list_videos() -> dict[str, Any]:
    """Scan `.repollama_data/videos/` and return available video files."""
    video_dir = Path(".repollama_data/videos")
    if not video_dir.exists():
        video_dir.mkdir(parents=True, exist_ok=True)

    videos = []
    supported_exts = {".webm", ".mp4", ".mov", ".avi"}

    for p in video_dir.glob("*"):
        if p.is_file() and p.suffix.lower() in supported_exts:
            stat = p.stat()
            videos.append({
                "filename": p.name,
                "title": p.stem.replace("_", " ").title(),
                "url": f"/api/v1/videos/stream/{p.name}",
                "size_bytes": stat.st_size,
                "created_at": stat.st_mtime,
                "format": p.suffix.lstrip(".").lower(),
            })

    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return {"videos": videos}


from fastapi.responses import FileResponse


@app.get("/api/v1/videos/stream/{filename}")
async def stream_video(filename: str):
    """Stream video file for playback."""
    video_path = Path(".repollama_data/videos") / filename
    if not video_path.exists() or not video_path.is_file():
        return {"error": "Video not found"}
    media_type = "video/webm" if filename.endswith(".webm") else "video/mp4"
    return FileResponse(path=video_path, media_type=media_type, filename=filename)


# ---------------------------------------------------------------------------
# Governance & CI/CD Gatekeeper Endpoints
# ---------------------------------------------------------------------------

class CICheckRequest(BaseModel):
    path: Optional[str] = Field(default=None, description="Path to repo workspace")
    base_ref: str = Field(default="HEAD~1", description="Base git reference")
    target_ref: str = Field(default="HEAD", description="Target git reference")
    role: str = Field(default="developer", description="User role ('developer' or 'architect')")


@app.post("/api/v1/governance/ci-check")
@app.post("/api/v1/ci-check")
async def run_ci_check(req: CICheckRequest) -> dict[str, Any]:
    """Run CI/CD Gatekeeper check on repository PR."""
    from repollama.engines.ci_gatekeeper import CIGatekeeper
    from repollama.core.enterprise import AuditLogger, RBACManager

    target_dir = Path(req.path).resolve() if req.path else Path.cwd()
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Invalid repository path: {req.path}")

    # Log action in audit log
    try:
        logger = AuditLogger()
        logger.log_action(f"CI Gatekeeper check executed by {req.role} (base: {req.base_ref}, target: {req.target_ref})")
    except Exception as e:
        pass

    gatekeeper = CIGatekeeper()
    try:
        report = await gatekeeper.evaluate_pr(target_dir, req.base_ref, req.target_ref)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gatekeeper evaluation error: {str(e)}")

    passed = report.get("passed", False)
    drift_report = report.get("drift", {})
    highest_debt_score = report.get("highest_debt_score", 0)

    # Check for added dependencies (drift)
    has_drift = False
    for changes in drift_report.values():
        if isinstance(changes, dict) and changes.get("added"):
            has_drift = True
            break

    # RBAC evaluation
    rbac = RBACManager()
    bypassed = False
    if has_drift and rbac.has_permission(req.role, "bypass_drift"):
        bypassed = True
        passed = (highest_debt_score <= 80)

    return {
        "status": "success",
        "passed": passed,
        "bypassed": bypassed,
        "highest_debt_score": highest_debt_score,
        "has_drift": has_drift,
        "drift": drift_report,
        "base_ref": req.base_ref,
        "target_ref": req.target_ref,
        "role": req.role,
        "message": "PR passed quality gates" if passed else "PR failed quality gates",
    }


@app.get("/api/v1/governance/audit-log")
@app.get("/api/v1/audit-log")
async def get_audit_log(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    """Fetch the last N lines of the enterprise audit log."""
    log_path = Path(".repollama_data/enterprise_audit.log")
    if not log_path.exists():
        return {
            "status": "success",
            "exists": False,
            "path": str(log_path),
            "lines": [],
            "total_lines": 0
        }

    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
        all_lines = [line.strip() for line in content.splitlines() if line.strip()]
        recent_lines = all_lines[-limit:]
        return {
            "status": "success",
            "exists": True,
            "path": str(log_path),
            "lines": recent_lines,
            "total_lines": len(all_lines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read audit log: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "repollama.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )


