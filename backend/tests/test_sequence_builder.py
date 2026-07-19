from __future__ import annotations
import pytest
from repollama.engines.sequence_builder import SequenceDiagramBuilder


def test_sequence_diagram_builder_empty_traffic() -> None:
    action = "Sign Up"
    traffic = []

    diagram = SequenceDiagramBuilder.generate(action, traffic)

    expected = (
        "sequenceDiagram\n"
        "    actor User\n"
        "    participant Browser\n"
        "    participant Backend\n"
        '    User->>Browser: Clicks "Sign Up"'
    )
    assert diagram == expected


def test_sequence_diagram_builder_with_traffic() -> None:
    action = "Login"
    traffic = [
        {
            "url": "http://example.com/api/v1/login",
            "method": "POST",
            "status": 200,
        },
        {
            "url": "http://example.com/api/v1/user/profile?ref=nav",
            "method": "GET",
            "status": 200,
        },
        {
            "url": "http://example.com/api/v1/error-endpoint",
            "method": "GET",
            "status": 500,
        },
        {
            "url": "http://example.com/api/v1/pending",
            "method": "GET",
            "status": None,
        }
    ]

    diagram = SequenceDiagramBuilder.generate(action, traffic)

    expected = (
        "sequenceDiagram\n"
        "    actor User\n"
        "    participant Browser\n"
        "    participant Backend\n"
        '    User->>Browser: Clicks "Login"\n'
        "    Browser->>Backend: POST /api/v1/login\n"
        "    Backend-->>Browser: 200\n"
        "    Browser->>Backend: GET /api/v1/user/profile\n"
        "    Backend-->>Browser: 200\n"
        "    Browser->>Backend: GET /api/v1/error-endpoint\n"
        "    Backend-->>Browser: 500\n"
        "    Browser->>Backend: GET /api/v1/pending\n"
        "    Backend-->>Browser: Pending"
    )
    assert diagram == expected
