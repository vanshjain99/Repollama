from __future__ import annotations
from typing import Any
import networkx as nx


class KnowledgeGraphBuilder:
    """Builder for orchestrating and managing a deterministic codebase Knowledge Graph.

    Tracks files, classes, functions, and imports as nodes and edges in a directed graph.
    """

    def __init__(self) -> None:
        """Initialize an empty directed graph using networkx.DiGraph."""
        self.graph = nx.DiGraph()

    def add_file_node(self, file_path: str, metadata: dict[str, Any]) -> None:
        """Add a node representing a file.

        Args:
            file_path: The unique path of the file.
            metadata: Additional metadata attributes (e.g. language, size).
        """
        self.graph.add_node(file_path, type="file", **metadata)

    def add_code_node(self, name: str, type: str, file_path: str) -> None:
        """Add a node for a class or function and link it to its parent file via a CONTAINS edge.

        Uses a composite key for code nodes to avoid name collisions across files.

        Args:
            name: The name of the class or function.
            type: The node type (typically 'class' or 'function').
            file_path: The parent file path.
        """
        node_key = f"{file_path}::{name}"
        self.graph.add_node(node_key, name=name, type=type, file_path=file_path)

        # Ensure the parent file node exists
        if not self.graph.has_node(file_path):
            self.graph.add_node(file_path, type="file")

        self.graph.add_edge(file_path, node_key, type="CONTAINS")

    def add_import_edge(self, source_file: str, imported_module: str) -> None:
        """Create an IMPORTS directed edge between the source file and an imported file or module.

        Args:
            source_file: The file containing the import statement.
            imported_module: The name/path of the module or file being imported.
        """
        if not self.graph.has_node(source_file):
            self.graph.add_node(source_file, type="file")
        if not self.graph.has_node(imported_module):
            self.graph.add_node(imported_module, type="module")

        self.graph.add_edge(source_file, imported_module, type="IMPORTS")

    def get_graph_stats(self) -> dict[str, int]:
        """Return the current number of nodes and edges in the Knowledge Graph.

        Returns:
            A dictionary containing 'node_count' and 'edge_count'.
        """
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
        }
