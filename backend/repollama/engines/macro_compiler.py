from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import networkx as nx

from repollama.engines.ast_parser import ASTParser
from repollama.engines.graph_builder import KnowledgeGraphBuilder


class MacroCompiler:
    """Engine to merge multiple codebases and map cross-repository references."""

    def __init__(self) -> None:
        """Initialize MacroCompiler with an empty DiGraph."""
        self.macro_graph = nx.DiGraph()

    def compile(self, repo_paths: list[str]) -> nx.DiGraph:
        """Scan each repository path, parse files via ASTParser, and merge their graphs.

        Args:
            repo_paths: List of file directory paths to repositories.

        Returns:
            The combined macro directed graph.
        """
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

        for path in repo_paths:
            target_dir = Path(path).resolve()
            repo_name = target_dir.name

            # Instantiate a namespace-aware builder
            builder = KnowledgeGraphBuilder(repo_name=repo_name)

            for path_obj in target_dir.rglob("*"):
                if not path_obj.is_file():
                    continue

                relative_path = path_obj.relative_to(target_dir)
                if any(part in exclude_dirs for part in relative_path.parts):
                    continue

                if path_obj.suffix.lower() not in supported_extensions:
                    continue

                file_path_str = str(relative_path)
                file_key = str(path_obj.resolve())

                try:
                    ast_meta = parser.parse_file(path_obj)

                    # Tag the file node with language and relative path
                    builder.add_file_node(file_key, {
                        "language": ast_meta.language,
                        "relative_path": file_path_str
                    })

                    for cls in ast_meta.classes:
                        builder.add_code_node(cls.name, "class", file_key)

                    for func in ast_meta.functions:
                        builder.add_code_node(func.name, "function", file_key)

                    for imp in ast_meta.imports:
                        builder.add_import_edge(file_key, imp)

                except Exception:
                    # Non-fatal parsing issues are skipped
                    pass

            self.macro_graph = nx.compose(self.macro_graph, builder.graph)

        return self.macro_graph

    def resolve_cross_links(self) -> None:
        """Heuristically identify and add CROSS_REPO_LINK edges between repositories.

        Checks if imports in Repo A match top-level folder names or root modules mapped in Repo B.
        """
        # Group file nodes by repository name
        repo_files: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for node, data in self.macro_graph.nodes(data=True):
            if data.get("type") == "file":
                r_name = data.get("repo_name")
                if r_name:
                    if r_name not in repo_files:
                        repo_files[r_name] = []
                    repo_files[r_name].append((node, data))

        repo_names = list(repo_files.keys())
        edges_to_add: list[tuple[str, str]] = []

        def extract_module_path(import_str: str) -> str:
            # JS/TS quotes extraction
            match = re.search(r"['\"`]([^'\"`]+)['\"`]", import_str)
            if match:
                return match.group(1)
            
            # Python import extraction
            if import_str.startswith("from "):
                parts = import_str.split()
                if len(parts) > 1:
                    return parts[1]
            elif import_str.startswith("import "):
                parts = import_str.split()
                if len(parts) > 1:
                    return parts[1]
            return import_str

        for u, v, edge_data in list(self.macro_graph.edges(data=True)):
            if edge_data.get("type") != "IMPORTS":
                continue

            u_data = self.macro_graph.nodes[u]
            u_repo = u_data.get("repo_name")
            if not u_repo:
                continue

            import_str = str(v)
            extracted_import = extract_module_path(import_str)

            for other_repo in repo_names:
                if other_repo == u_repo:
                    continue

                # Heuristic: Check if the import path matches/prefixes the target repository namespace
                if (
                    extracted_import == other_repo
                    or extracted_import.startswith(f"{other_repo}/")
                    or extracted_import.startswith(f"{other_repo}.")
                ):
                    # Find matching file/folder in the other repository
                    suffix = extracted_import[len(other_repo):].strip("/.")
                    matched = False
                    for f_node, f_data in repo_files[other_repo]:
                        rel_path = f_data.get("relative_path", "")
                        # Match relative path segments or file stems
                        if suffix and (suffix in rel_path or Path(rel_path).stem == suffix):
                            edges_to_add.append((u, f_node))
                            matched = True

                    if not matched:
                        # Fallback to typical entry points (main, index, app) or first file
                        main_files = [
                            f_node for f_node, f_data in repo_files[other_repo]
                            if any(k in (f_data.get("relative_path") or f_node).lower() for k in ["main", "index", "app"])
                        ]
                        if main_files:
                            for mf in main_files:
                                edges_to_add.append((u, mf))
                        elif repo_files[other_repo]:
                            edges_to_add.append((u, repo_files[other_repo][0][0]))

        # Add all resolved cross-repo edges to the macro graph
        for src, dest in edges_to_add:
            self.macro_graph.add_edge(src, dest, type="CROSS_REPO_LINK")
