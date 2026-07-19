from __future__ import annotations
import pytest
import networkx as nx
from repollama.engines.debt_evaluator import DebtEvaluator


@pytest.mark.anyio
async def test_debt_evaluator_scoring_and_sorting() -> None:
    # Construct a mock NetworkX DiGraph
    graph = nx.DiGraph()

    # 1. Add file nodes
    graph.add_node("file1.py", type="file")
    graph.add_node("file2.py", type="file")
    graph.add_node("file3.py", type="file")

    # 2. Add code nodes and contains edges
    # file1.py contains class A and function B (complexity = 2)
    graph.add_node("file1.py::A", type="class", name="A", file_path="file1.py")
    graph.add_edge("file1.py", "file1.py::A", type="CONTAINS")
    graph.add_node("file1.py::B", type="function", name="B", file_path="file1.py")
    graph.add_edge("file1.py", "file1.py::B", type="CONTAINS")

    # file2.py contains class C (complexity = 1)
    graph.add_node("file2.py::C", type="class", name="C", file_path="file2.py")
    graph.add_edge("file2.py", "file2.py::C", type="CONTAINS")

    # file3.py has no classes/functions (complexity = 0)

    # 3. Add import edges
    # file2.py imports file1.py (adds import edge file2.py -> file1.py)
    # This contributes 1 outgoing coupling to file2.py, 1 incoming coupling to file1.py
    graph.add_edge("file2.py", "file1.py", type="IMPORTS")
    # file1.py imports file3.py (adds import edge file1.py -> file3.py)
    # This contributes 1 outgoing coupling to file1.py, 1 incoming coupling to file3.py
    graph.add_edge("file1.py", "file3.py", type="IMPORTS")

    # Coupling summary:
    # file1.py: 1 incoming, 1 outgoing = 2
    # file2.py: 0 incoming, 1 outgoing = 1
    # file3.py: 1 incoming, 0 outgoing = 1

    # Churn map
    file_churn = {
        "file1.py": 5,
        "file2.py": 2,
        # file3.py is not in the map, so it will default to 1
    }

    evaluator = DebtEvaluator(graph, file_churn)
    results = await evaluator.evaluate()

    # Verify results count
    assert len(results) == 3

    # Calculations:
    # file1.py:
    #   coupling = 2
    #   complexity = 2
    #   churn = 5
    #   score = min(100, (2 * 1.5) + (2 * 2.0) * (5 * 0.5)) = min(100, 3 + 4 * 2.5) = min(100, 13) = 13
    # file2.py:
    #   coupling = 1
    #   complexity = 1
    #   churn = 2
    #   score = min(100, (1 * 1.5) + (1 * 2.0) * (2 * 0.5)) = min(100, 1.5 + 2 * 1.0) = min(100, 3.5) = 4 (rounded)
    # file3.py:
    #   coupling = 1
    #   complexity = 0
    #   churn = 1 (defaulted)
    #   score = min(100, (1 * 1.5) + (0 * 2.0) * (1 * 0.5)) = min(100, 1.5 + 0) = min(100, 1.5) = 2 (rounded)

    # Output sorting should be file1.py (13), file2.py (4), file3.py (2)
    assert results[0]["file"] == "file1.py"
    assert results[0]["coupling"] == 2
    assert results[0]["complexity"] == 2
    assert results[0]["churn"] == 5
    assert results[0]["score"] == 13

    assert results[1]["file"] == "file2.py"
    assert results[1]["coupling"] == 1
    assert results[1]["complexity"] == 1
    assert results[1]["churn"] == 2
    assert results[1]["score"] == 4

    assert results[2]["file"] == "file3.py"
    assert results[2]["coupling"] == 1
    assert results[2]["complexity"] == 0
    assert results[2]["churn"] == 1  # defaulted
    assert results[2]["score"] == 2


@pytest.mark.anyio
async def test_debt_evaluator_cap_at_100() -> None:
    # Construct a mock NetworkX DiGraph
    graph = nx.DiGraph()
    graph.add_node("heavy_debt.py", type="file")

    # Add high complexity (20 CONTAINS edges)
    for i in range(20):
        node_key = f"heavy_debt.py::func_{i}"
        graph.add_node(node_key, type="function", name=f"func_{i}", file_path="heavy_debt.py")
        graph.add_edge("heavy_debt.py", node_key, type="CONTAINS")

    # Churn is high (50)
    file_churn = {"heavy_debt.py": 50}

    evaluator = DebtEvaluator(graph, file_churn)
    results = await evaluator.evaluate()

    assert len(results) == 1
    assert results[0]["file"] == "heavy_debt.py"
    # score calculation: coupling = 0, complexity = 20, churn = 50
    # raw_score = (0 * 1.5) + (20 * 2.0) * (50 * 0.5) = 0 + 40 * 25 = 1000
    # score capped at 100
    assert results[0]["score"] == 100
