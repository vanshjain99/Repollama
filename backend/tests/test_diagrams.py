from __future__ import annotations
import pytest
from repollama.engines.diagram_generator import DiagramGenerator


def test_generate_c4_context() -> None:
    stats = {"node_count": 12, "edge_count": 24}
    c4 = DiagramGenerator.generate_c4_context(stats)
    assert "C4Context" in c4
    assert "System Context diagram for Repollama" in c4
    assert "Developer" in c4
    assert "12 nodes" in c4
    assert "24 edges" in c4


def test_generate_c4_context_alternative_keys() -> None:
    stats = {"nodes": 15, "edges": 30}
    c4 = DiagramGenerator.generate_c4_context(stats)
    assert "C4Context" in c4
    assert "15 nodes" in c4
    assert "30 edges" in c4


def test_generate_erd_empty() -> None:
    erd = DiagramGenerator.generate_erd([])
    assert "erDiagram" in erd
    assert "No classes defined" in erd


def test_generate_erd_classes() -> None:
    classes = [
        {"name": "DataManager"},
        {"name": "UserAccount"},
        {"name": "Invalid-Class-Name!"},
    ]
    erd = DiagramGenerator.generate_erd(classes)
    assert "erDiagram" in erd
    assert "Repository ||--o{ DataManager : contains" in erd
    assert "Repository ||--o{ UserAccount : contains" in erd
    # Verify sanitization replaces special characters
    assert "Repository ||--o{ InvalidClassName : contains" in erd
