import asyncio
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Query
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

# Add CORS middleware to allow connections from local UI wrappers (like Tauri/React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local-first Tauri apps, allowing all origins is standard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

        yield {
            "data": (
                f"[System] Analysis complete. Nodes: {node_count}, "
                f"Edges: {edge_count}, Collection Size: {vs_size}"
            )
        }
        yield {"data": "[Pipeline] Analysis Complete!"}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "repollama.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )

