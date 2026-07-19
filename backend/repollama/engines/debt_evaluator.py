from __future__ import annotations
from typing import Any
import networkx as nx


class DebtEvaluator:
    """Evaluates the technical debt of files in the codebase Knowledge Graph.

    Synthesizes Knowledge Graph dependencies and git churn to mathematically
    identify the riskiest, most debt-ridden files.
    """

    def __init__(self, graph: nx.DiGraph, file_churn: dict[str, int]) -> None:
        """Initialize DebtEvaluator.

        Args:
            graph: The NetworkX DiGraph representing the codebase Knowledge Graph.
            file_churn: A dictionary mapping file paths to their modification/commit count.
        """
        self.graph = graph
        self.file_churn = file_churn

    async def evaluate(self) -> list[dict[str, Any]]:
        """Calculate the maintainability/debt score for all files in the Knowledge Graph.

        Returns:
            A list of dicts, sorted from Highest Debt to Lowest Debt:
            [{"file": "src/main.py", "coupling": 12, "complexity": 8, "churn": 25, "score": 94}, ...]
        """
        results: list[dict[str, Any]] = []

        # Find all nodes in the graph that represent files
        file_nodes = [
            node for node, attrs in self.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]

        for file_node in file_nodes:
            # 1. Coupling: incoming and outgoing IMPORTS edges
            incoming_imports = sum(
                1 for _, _, data in self.graph.in_edges(file_node, data=True)
                if data.get("type") == "IMPORTS"
            )
            outgoing_imports = sum(
                1 for _, _, data in self.graph.out_edges(file_node, data=True)
                if data.get("type") == "IMPORTS"
            )
            coupling = incoming_imports + outgoing_imports

            # 2. Complexity: CONTAINS edges from this file
            complexity = sum(
                1 for _, _, data in self.graph.out_edges(file_node, data=True)
                if data.get("type") == "CONTAINS"
            )

            # 3. Churn: edit count from the file_churn dict (default to 1 if not found)
            churn = self.file_churn.get(file_node, 1)

            # 4. Debt Score: (Coupling * 1.5) + (Complexity * 2.0) * (Churn * 0.5)
            # Cap at 100.
            raw_score = (coupling * 1.5) + (complexity * 2.0) * (churn * 0.5)
            score = min(100, max(0, round(raw_score)))

            results.append({
                "file": file_node,
                "coupling": coupling,
                "complexity": complexity,
                "churn": churn,
                "score": score,
            })

        # Sort from highest score to lowest score, sub-sorted alphabetically for deterministic output
        results.sort(key=lambda x: (-x["score"], x["file"]))

        return results
