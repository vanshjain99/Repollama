from __future__ import annotations
from pathlib import Path
from typing import Any


class PerformanceAuditor:
    """Scans repository files and AST metadata for performance bottlenecks.

    Identifies bloated functions and potential N+1 database queries in loop constructs.
    """

    def __init__(self, file_contents: dict[str, str] | None = None) -> None:
        """Initialize PerformanceAuditor.

        Args:
            file_contents: Optional dictionary mapping file paths to their in-memory raw string content.
                           Used to avoid re-reading files from disk, especially during testing.
        """
        self.file_contents = file_contents or {}

    def detect_anti_patterns(self, ast_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Scan AST structures and code lines for bloated functions and N+1 query loops.

        Args:
            ast_data: A list of dicts representing AST metadata of parsed files.

        Returns:
            A list of flag dictionaries representing performance bottlenecks:
            [{"file": "src/users.py", "issue": "Bloated function (150 lines)", "severity": "Medium", "target": "process_users"}]
        """
        flags: list[dict[str, Any]] = []

        for file_ast in ast_data:
            file_path = file_ast.get("file_path", "")
            functions = file_ast.get("functions", [])
            language = file_ast.get("language", "python")

            # Load file content if possible
            content = self.file_contents.get(file_path)
            if not content:
                try:
                    path = Path(file_path)
                    if path.exists() and path.is_file():
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                except Exception:
                    pass

            file_lines = content.splitlines() if content else []

            for func in functions:
                name = func.get("name", "Unknown")
                start_line = func.get("start_line", 1)
                end_line = func.get("end_line", 1)

                span = end_line - start_line + 1

                # 1. Bloated function detection (> 100 lines)
                if span > 100:
                    flags.append({
                        "file": file_path,
                        "issue": f"Bloated function ({span} lines)",
                        "severity": "Medium",
                        "target": name
                    })

                # 2. N+1 query loop detection
                if file_lines and 1 <= start_line <= len(file_lines):
                    # Extract the lines of the function body
                    # end_line is inclusive and 1-indexed, so slice represents start_line-1 to end_line
                    func_lines = file_lines[start_line - 1 : end_line]
                    if self._has_n1_query(func_lines, language):
                        flags.append({
                            "file": file_path,
                            "issue": "Potential N+1 query loop",
                            "severity": "High",
                            "target": name
                        })

        return flags

    def _has_n1_query(self, lines: list[str], language: str) -> bool:
        """Scan function body lines to detect database or HTTP requests inside loop blocks.

        Args:
            lines: List of raw string lines for the function body.
            language: The language identifier ('python', 'javascript', 'typescript', 'tsx').

        Returns:
            bool: True if an N+1 query pattern is found, False otherwise.
        """
        orm_methods = [".find(", ".select(", ".query(", ".execute("]

        if language == "python":
            in_loop = False
            loop_indent = -1
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                indent = len(line) - len(line.lstrip())

                if in_loop:
                    if indent <= loop_indent:
                        in_loop = False
                        loop_indent = -1
                    else:
                        # Check for ORM methods or await/async HTTP requests inside loop
                        if any(method in stripped for method in orm_methods) or "await " in stripped:
                            return True

                # Check if a new loop is started
                if not in_loop and (stripped.startswith("for ") or stripped.startswith("while ")):
                    in_loop = True
                    loop_indent = indent

        else:
            # JS/TS/TSX brace-based loop check
            in_loop = False
            brace_count = 0
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                    continue

                if in_loop:
                    brace_count += stripped.count("{") - stripped.count("}")
                    # Check for ORM methods or await inside loop block
                    if any(method in stripped for method in orm_methods) or "await " in stripped:
                        return True
                    if brace_count <= 0:
                        in_loop = False

                # Check if a new loop is started
                # Examples: for (const x of y) {, while (x) {, items.map(item => {
                if not in_loop:
                    is_loop = (
                        stripped.startswith("for ") or
                        stripped.startswith("for(") or
                        stripped.startswith("while ") or
                        stripped.startswith("while(") or
                        ".forEach(" in stripped or
                        ".map(" in stripped
                    )
                    if is_loop:
                        in_loop = True
                        brace_count = stripped.count("{") - stripped.count("}")

        return False
