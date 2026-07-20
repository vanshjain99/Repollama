from repollama.engines.graph_builder import KnowledgeGraphBuilder


def test_graph_builder_initialization():
    builder = KnowledgeGraphBuilder()
    stats = builder.get_graph_stats()
    assert stats["node_count"] == 0
    assert stats["edge_count"] == 0


def test_add_file_node():
    builder = KnowledgeGraphBuilder()
    builder.add_file_node("src/main.py", {"language": "python", "size": 1024})
    stats = builder.get_graph_stats()
    assert stats["node_count"] == 1
    assert stats["edge_count"] == 0

    assert builder.graph.nodes["src/main.py"]["type"] == "file"
    assert builder.graph.nodes["src/main.py"]["language"] == "python"
    assert builder.graph.nodes["src/main.py"]["size"] == 1024


def test_add_code_node():
    builder = KnowledgeGraphBuilder()
    # Adding a code node will automatically verify/add the parent file node if missing
    builder.add_code_node("DataManager", "class", "src/db.py")

    stats = builder.get_graph_stats()
    # Should have 2 nodes: "src/db.py" and "src/db.py::DataManager"
    assert stats["node_count"] == 2
    assert stats["edge_count"] == 1

    node_key = "src/db.py::DataManager"
    assert builder.graph.nodes[node_key]["name"] == "DataManager"
    assert builder.graph.nodes[node_key]["type"] == "class"
    assert builder.graph.nodes[node_key]["file_path"] == "src/db.py"

    # Edge checks
    assert builder.graph.has_edge("src/db.py", node_key)
    assert builder.graph.edges["src/db.py", node_key]["type"] == "CONTAINS"


def test_add_import_edge():
    builder = KnowledgeGraphBuilder()
    builder.add_import_edge("src/main.py", "os")

    stats = builder.get_graph_stats()
    # Should have 2 nodes: "src/main.py" and "os"
    assert stats["node_count"] == 2
    assert stats["edge_count"] == 1

    assert builder.graph.nodes["src/main.py"]["type"] == "file"
    assert builder.graph.nodes["os"]["type"] == "module"

    assert builder.graph.has_edge("src/main.py", "os")
    assert builder.graph.edges["src/main.py", "os"]["type"] == "IMPORTS"


def test_get_graph_stats():
    builder = KnowledgeGraphBuilder()
    builder.add_file_node("file1.py", {"language": "python"})
    builder.add_code_node("func1", "function", "file1.py")
    builder.add_import_edge("file1.py", "sys")

    stats = builder.get_graph_stats()
    # Nodes: "file1.py", "file1.py::func1", "sys"
    assert stats["node_count"] == 3
    # Edges: "file1.py" -> "file1.py::func1" (CONTAINS), "file1.py" -> "sys" (IMPORTS)
    assert stats["edge_count"] == 2


def test_remove_file_subgraph():
    builder = KnowledgeGraphBuilder()

    # Setup: 2 files, one has functions/classes, one is imported.
    builder.add_file_node("file1.py", {"language": "python"})
    builder.add_code_node("ClassA", "class", "file1.py")
    builder.add_code_node("func1", "function", "file1.py")
    builder.add_import_edge("file1.py", "sys")
    builder.add_import_edge("file1.py", "file2.py")

    # file2.py exists and contains ClassB.
    builder.add_file_node("file2.py", {"language": "python"})
    builder.add_code_node("ClassB", "class", "file2.py")

    stats = builder.get_graph_stats()
    assert stats["node_count"] == 6
    assert stats["edge_count"] == 5

    # Act: remove file1.py's subgraph
    builder.remove_file_subgraph("file1.py")

    # Check updated stats
    stats_after = builder.get_graph_stats()
    assert stats_after["node_count"] == 3
    assert not builder.graph.has_node("file1.py")
    assert not builder.graph.has_node("file1.py::ClassA")
    assert not builder.graph.has_node("file1.py::func1")
    assert builder.graph.has_node("file2.py")
    assert builder.graph.has_node("file2.py::ClassB")
    assert builder.graph.has_node("sys")

    assert stats_after["edge_count"] == 1
    assert builder.graph.has_edge("file2.py", "file2.py::ClassB")

    # Act: remove a non-existent file path should return gracefully
    builder.remove_file_subgraph("non_existent.py")
    assert builder.get_graph_stats() == stats_after


def test_incremental_graph_patching():
    builder = KnowledgeGraphBuilder()

    # Initial state for file1.py: has old_func
    builder.add_file_node("file1.py", {"language": "python"})
    builder.add_code_node("old_func", "function", "file1.py")

    assert builder.graph.has_node("file1.py::old_func")

    # Patch file1.py: remove subgraph and re-add with new_func
    builder.remove_file_subgraph("file1.py")
    assert not builder.graph.has_node("file1.py::old_func")
    assert not builder.graph.has_node("file1.py")

    builder.add_file_node("file1.py", {"language": "python"})
    builder.add_code_node("new_func", "function", "file1.py")

    assert builder.graph.has_node("file1.py")
    assert builder.graph.has_node("file1.py::new_func")
    assert not builder.graph.has_node("file1.py::old_func")


