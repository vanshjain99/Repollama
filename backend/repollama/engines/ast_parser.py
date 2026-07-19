from __future__ import annotations
from pathlib import Path
from typing import Any
from pydantic import BaseModel
from tree_sitter import Language, Parser

# Pydantic models to store structural metadata
class ClassMetadata(BaseModel):
    name: str
    start_line: int
    end_line: int


class FunctionMetadata(BaseModel):
    name: str
    start_line: int
    end_line: int


class ASTMetadata(BaseModel):
    file_path: str
    language: str
    imports: list[str]
    classes: list[ClassMetadata]
    functions: list[FunctionMetadata]


class UnsupportedLanguageError(ValueError):
    """Exception raised when a file extension is not supported by the parser."""
    pass


# Tree-sitter queries for Python
# We target import statements, class definitions, and function/method definitions.
PYTHON_QUERY_SRC = """
; Imports
(import_statement) @import
(import_from_statement) @import

; Classes
(class_definition) @class

; Functions / Methods
(function_definition) @function
"""

# Tree-sitter queries for JavaScript/TypeScript (including JSX/TSX)
# We target imports, class declarations, and various function styles:
# 1. Standard function declarations: function foo() {}
# 2. Generator function declarations: function* foo() {}
# 3. Method definitions inside classes/objects: myMethod() {}
# 4. Arrow functions assigned to variables: const foo = () => {}
JS_TS_QUERY_SRC = """
; Imports
(import_statement) @import

; Classes
(class_declaration) @class

; Functions
(function_declaration) @function
(generator_function_declaration) @function
(method_definition) @function
(variable_declarator name: (identifier) value: (arrow_function)) @function
"""


class ASTParser:
    """ASTParser uses Tree-sitter queries to extract imports, classes, and functions from source files."""

    def __init__(self) -> None:
        # Import language libraries
        import tree_sitter_python as tspython
        import tree_sitter_javascript as tsjs
        import tree_sitter_typescript as tsts

        # Load languages using the tree-sitter 0.21.0+ API
        self._languages = {
            "python": Language(tspython.language()),
            "javascript": Language(tsjs.language()),
            "typescript": Language(tsts.language_typescript()),
            "tsx": Language(tsts.language_tsx()),
        }

        # Initialize queries for each supported language module
        self._queries = {
            "python": self._languages["python"].query(PYTHON_QUERY_SRC),
            "javascript": self._languages["javascript"].query(JS_TS_QUERY_SRC),
            "typescript": self._languages["typescript"].query(JS_TS_QUERY_SRC),
            "tsx": self._languages["tsx"].query(JS_TS_QUERY_SRC),
        }

    def get_language_from_extension(self, extension: str) -> str | None:
        """Map file extension to internal language key.

        Args:
            extension (str): File extension (e.g., '.py', '.tsx')

        Returns:
            str | None: Internal language name if supported, else None.
        """
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
        }
        return ext_map.get(ext)

    def parse_file(self, file_path: str | Path) -> ASTMetadata:
        """Read a source code file, detect language, parse and extract metadata.

        Args:
            file_path (str | Path): Path to the source file.

        Returns:
            ASTMetadata: Extracted metadata model.

        Raises:
            FileNotFoundError: If the target file does not exist.
            UnsupportedLanguageError: If the file extension is not supported.
            IOError: If reading the file fails.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        lang_name = self.get_language_from_extension(path.suffix)
        if not lang_name:
            raise UnsupportedLanguageError(
                f"Unsupported file extension '{path.suffix}' for path: {path}"
            )

        try:
            with open(path, "rb") as f:
                source_code = f.read()
        except Exception as e:
            raise IOError(f"Failed to read file {path}: {e}")

        return self.parse_content(source_code, lang_name, str(path))

    def parse_raw(self, content: bytes | str, extension: str) -> dict:
        """Parse raw content from memory using file extension.

        Args:
            content (bytes | str): The source code content.
            extension (str): The file extension (e.g., '.py', '.ts').

        Returns:
            dict: The dictionary representation of ASTMetadata.

        Raises:
            UnsupportedLanguageError: If the extension is not supported.
        """
        lang_name = self.get_language_from_extension(extension)
        if not lang_name:
            raise UnsupportedLanguageError(
                f"Unsupported file extension '{extension}' for raw content parsing."
            )

        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        metadata = self.parse_content(content_bytes, lang_name, "")
        return metadata.model_dump()

    def parse_content(self, source_code: bytes, lang_name: str, file_path: str = "") -> ASTMetadata:
        """Parse source code content directly from bytes and run queries to extract symbols.

        Args:
            source_code (bytes): Source code content as bytes.
            lang_name (str): Key of the language to use ('python', 'javascript', etc.)
            file_path (str): Optional file path for metadata recording.

        Returns:
            ASTMetadata: Extracted symbols.
        """
        language = self._languages.get(lang_name)
        query = self._queries.get(lang_name)
        if not language or not query:
            raise UnsupportedLanguageError(
                f"Language '{lang_name}' is not loaded or configured."
            )

        # Create parser initialized with the language
        parser = Parser(language)
        tree = parser.parse(source_code)

        # Run query captures on root node
        captures = query.captures(tree.root_node)

        imports: list[str] = []
        classes: list[ClassMetadata] = []
        functions: list[FunctionMetadata] = []

        # Process imports
        for node in captures.get("import", []):
            import_text = source_code[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
            if import_text:
                imports.append(import_text)

        # Process classes
        for node in captures.get("class", []):
            class_name = self._get_node_name(node, source_code)
            classes.append(
                ClassMetadata(
                    name=class_name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )

        # Process functions
        for node in captures.get("function", []):
            func_name = self._get_node_name(node, source_code)
            functions.append(
                FunctionMetadata(
                    name=func_name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )

        return ASTMetadata(
            file_path=file_path,
            language=lang_name,
            imports=imports,
            classes=classes,
            functions=functions,
        )

    def _get_node_name(self, node: Any, source_code: bytes) -> str:
        """Extract the name of a class or function node by query field name 'name'.

        Args:
            node: The Tree-sitter node.
            source_code (bytes): The full source code bytes.

        Returns:
            str: Extracted name or 'Unknown' if not resolved.
        """
        name_node = node.child_by_field_name("name")
        if name_node:
            return source_code[name_node.start_byte : name_node.end_byte].decode(
                "utf-8", errors="replace"
            )
        return "Unknown"
