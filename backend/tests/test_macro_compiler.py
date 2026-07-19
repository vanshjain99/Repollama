from __future__ import annotations
from pathlib import Path
import pytest
import networkx as nx

from repollama.engines.graph_builder import KnowledgeGraphBuilder
from repollama.engines.macro_compiler import MacroCompiler
from repollama.engines.diagram_generator import DiagramGenerator


def test_graph_builder_repo_name_tagging() -> None:
    """Verify that KnowledgeGraphBuilder tags all added nodes with repo_name."""
    builder = KnowledgeGraphBuilder(repo_name="my-test-repo")
    
    # 1. Add file node
    builder.add_file_node("src/main.py", {"language": "python"})
    assert builder.graph.nodes["src/main.py"]["repo_name"] == "my-test-repo"
    
    # 2. Add code node (automatically tags parent file and the code node key)
    builder.add_code_node("MyClass", "class", "src/helper.py")
    assert builder.graph.nodes["src/helper.py"]["repo_name"] == "my-test-repo"
    assert builder.graph.nodes["src/helper.py::MyClass"]["repo_name"] == "my-test-repo"
    
    # 3. Add import edge (automatically tags source file and imported module if missing)
    builder.add_import_edge("src/main.py", "os")
    assert builder.graph.nodes["os"]["repo_name"] == "my-test-repo"


def test_macro_compiler_compiles_and_merges(tmp_path: Path) -> None:
    """Verify that MacroCompiler compiles multiple repos and merges them with networkx.compose.

    Specifically checks that files with identical relative paths (e.g., main.py) do not collide
    because they are stored using their absolute path keys.
    """
    # Create Repo A (frontend)
    repo_a_dir = tmp_path / "frontend-app"
    repo_a_dir.mkdir()
    (repo_a_dir / "main.py").write_text("import os\n")
    (repo_a_dir / "src").mkdir()
    (repo_a_dir / "src" / "api.ts").write_text("import { getUser } from 'backend-api/users';\n")

    # Create Repo B (backend)
    repo_b_dir = tmp_path / "backend-api"
    repo_b_dir.mkdir()
    # Duplicate relative path main.py to test collision protection
    (repo_b_dir / "main.py").write_text("from helper import something\n")
    (repo_b_dir / "users.py").write_text("def get_user(): pass\n")

    # Run MacroCompiler compile
    compiler = MacroCompiler()
    repo_paths = [str(repo_a_dir), str(repo_b_dir)]
    macro_graph = compiler.compile(repo_paths)

    # Verify nodes count and metadata
    # Repo A files: main.py, src/api.ts. Repo B files: main.py, users.py.
    # Each repo file is identified by its absolute path.
    repo_a_main_key = str((repo_a_dir / "main.py").resolve())
    repo_b_main_key = str((repo_b_dir / "main.py").resolve())
    
    assert macro_graph.has_node(repo_a_main_key)
    assert macro_graph.has_node(repo_b_main_key)
    # The two main.py files should be distinct nodes in the graph
    assert repo_a_main_key != repo_b_main_key
    assert macro_graph.nodes[repo_a_main_key]["repo_name"] == "frontend-app"
    assert macro_graph.nodes[repo_b_main_key]["repo_name"] == "backend-api"

    # Verify that the relative paths are captured
    assert macro_graph.nodes[repo_a_main_key]["relative_path"] == "main.py"
    assert macro_graph.nodes[repo_b_main_key]["relative_path"] == "main.py"


def test_macro_compiler_resolve_cross_links(tmp_path: Path) -> None:
    """Verify that cross-repo import links are resolved correctly via the heuristic."""
    repo_a_dir = tmp_path / "frontend-app"
    repo_a_dir.mkdir()
    (repo_a_dir / "src").mkdir()
    (repo_a_dir / "src" / "api.ts").write_text("import { getUser } from 'backend-api/users';\n")

    repo_b_dir = tmp_path / "backend-api"
    repo_b_dir.mkdir()
    (repo_b_dir / "users.py").write_text("def get_user(): pass\n")

    compiler = MacroCompiler()
    repo_paths = [str(repo_a_dir), str(repo_b_dir)]
    macro_graph = compiler.compile(repo_paths)
    
    # Run cross-link resolution
    compiler.resolve_cross_links()

    # Find the CROSS_REPO_LINK edge
    api_ts_key = str((repo_a_dir / "src" / "api.ts").resolve())
    users_py_key = str((repo_b_dir / "users.py").resolve())

    assert macro_graph.has_edge(api_ts_key, users_py_key)
    assert macro_graph.edges[api_ts_key, users_py_key]["type"] == "CROSS_REPO_LINK"


def test_generate_macro_c4(tmp_path: Path) -> None:
    """Verify that DiagramGenerator generates a valid Mermaid C4 diagram from a macro graph."""
    repo_a_dir = tmp_path / "frontend-app"
    repo_a_dir.mkdir()
    (repo_a_dir / "src").mkdir()
    (repo_a_dir / "src" / "api.ts").write_text("import { getUser } from 'backend-api/users';\n")

    repo_b_dir = tmp_path / "backend-api"
    repo_b_dir.mkdir()
    (repo_b_dir / "users.py").write_text("def get_user(): pass\n")

    compiler = MacroCompiler()
    repo_paths = [str(repo_a_dir), str(repo_b_dir)]
    macro_graph = compiler.compile(repo_paths)
    compiler.resolve_cross_links()

    # Generate C4
    c4_diagram = DiagramGenerator.generate_macro_c4(macro_graph)

    # Verify structural elements of C4Context Mermaid
    assert "C4Context" in c4_diagram
    assert "title Macro Architecture Diagram" in c4_diagram
    assert "SystemBoundary(repo_a, \"frontend-app\")" in c4_diagram
    assert "SystemBoundary(repo_b, \"backend-api\")" in c4_diagram
    assert "Container(file_1, \"src/api.ts\", \"TypeScript\")" in c4_diagram
    assert "Container(file_2, \"users.py\", \"Python\")" in c4_diagram
    assert "Rel(file_1, file_2, \"CROSS_REPO_LINK\")" in c4_diagram
