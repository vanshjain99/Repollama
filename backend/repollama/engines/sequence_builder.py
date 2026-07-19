from __future__ import annotations
from typing import Any
from urllib.parse import urlparse


class SequenceDiagramBuilder:
    """Formatter to build Mermaid sequence diagrams from interaction logs and API traffic."""

    @staticmethod
    def generate(action: str, traffic: list[dict[str, Any]]) -> str:
        """Generate a Mermaid sequence diagram representation of the click and subsequent network traffic.

        Args:
            action: The text of the user action (e.g. click text).
            traffic: List of intercepted request/response dictionaries.

        Returns:
            str: Fully formatted Mermaid sequence diagram.
        """
        lines = [
            "sequenceDiagram",
            "    actor User",
            "    participant Browser",
            "    participant Backend",
            f'    User->>Browser: Clicks "{action}"'
        ]

        for req in traffic:
            url = req.get("url", "")
            method = req.get("method", "GET")
            status = req.get("status")
            status_str = str(status) if status is not None else "Pending"

            try:
                parsed = urlparse(url)
                path = parsed.path
                if not path:
                    path = "/"
            except Exception:
                path = url

            lines.append(f"    Browser->>Backend: {method} {path}")
            lines.append(f"    Backend-->>Browser: {status_str}")

        return "\n".join(lines)
