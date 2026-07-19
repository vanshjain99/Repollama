from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any, Optional
from fastapi import FastAPI, Query, Request
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


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Check the health status of the API and its connection to the Ollama service.

    Returns:
        A dictionary containing health and Ollama connection details.
    """
    ollama_reachable = await ollama_manager.ping_server()
    return {
        "status": "healthy",
        "ollama": {
            "connected": ollama_reachable,
            "base_url": settings.OLLAMA_BASE_URL,
            "default_model": settings.DEFAULT_MODEL,
        },
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


from pydantic import BaseModel


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "repollama.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )

