from __future__ import annotations
import re
from typing import Any


class DiagramGenerator:
    """Generates Mermaid diagrams (C4 Context, ERD) from repository metadata."""

    @staticmethod
    def generate_c4_context(graph_stats: dict) -> str:
        """Takes basic graph statistics or nodes and returns a valid Mermaid C4 Context diagram string.

        Args:
            graph_stats: Dictionary containing 'node_count' and 'edge_count' keys (or 'nodes' and 'edges').

        Returns:
            str: Valid Mermaid C4 Context diagram string.
        """
        node_count = graph_stats.get("node_count") or graph_stats.get("nodes", 0)
        edge_count = graph_stats.get("edge_count") or graph_stats.get("edges", 0)

        return (
            "C4Context\n"
            "  title System Context diagram for Repollama\n"
            "  Person(developer, \"Developer\", \"A software engineer.\")\n"
            f"  System(repollama, \"Repollama\", \"Allows developers to analyze repositories. Graph contains {node_count} nodes and {edge_count} edges.\")\n"
            "  Rel(developer, repollama, \"Uses\")"
        )

    @staticmethod
    def generate_erd(ast_classes: list[dict]) -> str:
        """Takes a list of extracted classes from the ASTParser and returns a valid Mermaid ER Diagram string.

        Args:
            ast_classes: List of class dictionaries containing at least a 'name' key.

        Returns:
            str: Valid Mermaid ER Diagram string.
        """
        lines = ["erDiagram"]
        if not ast_classes:
            lines.append("    Repository {")
            lines.append("        string status \"No classes defined\"")
            lines.append("    }")
        else:
            for cls in ast_classes:
                if isinstance(cls, dict):
                    name = cls.get("name")
                else:
                    name = getattr(cls, "name", None)

                if name:
                    entity_name = DiagramGenerator._sanitize_entity_name(name)
                    lines.append(f"    Repository ||--o{{ {entity_name} : contains")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_entity_name(name: str) -> str:
        """Sanitizes class name to be a valid Mermaid entity name.

        Mermaid entity names must start with an alpha character or underscore,
        and contain only alphanumeric characters or underscores.
        """
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "", name)
        if not sanitized:
            return "UnknownEntity"
        if not re.match(r"^[a-zA-Z_]", sanitized):
            sanitized = "_" + sanitized
        return sanitized

    @staticmethod
    def generate_macro_c4(macro_graph: Any) -> str:
        """Generate a Mermaid C4 diagram representing the macro repository architecture.

        Each repository is represented as a SystemBoundary containing Container elements for files.
        Cross-repository links are drawn using Rel.
        """
        lines = [
            "C4Context",
            "  title Macro Architecture Diagram"
        ]

        # Gather unique repo names and their files
        repo_nodes: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        node_to_alias: dict[str, str] = {}
        alias_counter = 1

        for node, data in macro_graph.nodes(data=True):
            if data.get("type") == "file":
                r_name = data.get("repo_name", "unknown_repo")
                if r_name not in repo_nodes:
                    repo_nodes[r_name] = []
                repo_nodes[r_name].append((node, data))

        # Generate SystemBoundary for each repo
        for repo_idx, (repo_name, files) in enumerate(repo_nodes.items(), start=1):
            # Create a clean repo alias (repo_a, repo_b, etc.)
            repo_alias = f"repo_{chr(96 + repo_idx)}" if repo_idx <= 26 else f"repo_{repo_idx}"

            lines.append(f"  SystemBoundary({repo_alias}, \"{repo_name}\") {{")
            for node, data in files:
                alias = f"file_{alias_counter}"
                alias_counter += 1
                node_to_alias[node] = alias

                # Format language
                lang = data.get("language", "Unknown")
                lang_display = {
                    "python": "Python",
                    "typescript": "TypeScript",
                    "javascript": "JavaScript",
                    "tsx": "TSX",
                    "jsx": "JSX"
                }.get(lang.lower(), lang.capitalize())

                rel_path = data.get("relative_path") or node
                lines.append(f"    Container({alias}, \"{rel_path}\", \"{lang_display}\")")
            lines.append("  }")

        # Add relations (CROSS_REPO_LINK edges)
        for u, v, edge_data in macro_graph.edges(data=True):
            if edge_data.get("type") == "CROSS_REPO_LINK":
                alias_u = node_to_alias.get(u)
                alias_v = node_to_alias.get(v)
                if alias_u and alias_v:
                    lines.append(f"  Rel({alias_u}, {alias_v}, \"CROSS_REPO_LINK\")")

        return "\n".join(lines)
