from __future__ import annotations
from pathlib import Path
import re
from typing import Any
from git import Repo
from repollama.engines.ast_parser import ASTParser, UnsupportedLanguageError


class DriftDetector:
    """DriftDetector compares AST-extracted imports/dependencies between two git refs/commits."""

    def __init__(self, repo_path: str | Path) -> None:
        """Initialize DriftDetector with the target git repository.

        Args:
            repo_path (str | Path): Path to the Git repository.
        """
        self.repo_path = Path(repo_path).resolve()
        self.repo = Repo(self.repo_path)
        self.parser = ASTParser()

    def detect_drift(
        self, base_ref: str = "HEAD~1", target_ref: str = "HEAD"
    ) -> dict[str, dict[str, list[str]]]:
        """Compare dependencies of files between base_ref and target_ref.

        Finds Python, JS, and TS files added or modified, extracts their imports in both
        states, and computes added/removed dependencies.

        Args:
            base_ref (str): Base commit reference (default "HEAD~1").
            target_ref (str): Target reference, e.g. "HEAD" or "working_dir".

        Returns:
            dict[str, dict[str, list[str]]]: Map of file path to dict of "added" and "removed" deps.
        """
        # Resolve base ref to commit object
        try:
            base_commit = self.repo.commit(base_ref)
        except Exception as e:
            raise ValueError(f"Could not resolve base reference '{base_ref}': {e}")

        # Determine if target_ref represents the working directory
        is_working_dir = False
        if target_ref is None:
            is_working_dir = True
        elif isinstance(target_ref, str):
            ref_lower = target_ref.lower()
            if ref_lower in ("working_dir", "working_tree", "worktree", "working"):
                is_working_dir = True

        # Diff base commit against target
        if is_working_dir:
            diffs = base_commit.diff(None)
        else:
            try:
                target_commit = self.repo.commit(target_ref)
                diffs = base_commit.diff(target_commit)
            except Exception as e:
                raise ValueError(f"Could not resolve target reference '{target_ref}': {e}")

        drift_results: dict[str, dict[str, list[str]]] = {}

        for d in diffs:
            # We are interested in modified ('M'), added ('A'), renamed ('R'), or copied ('C') files.
            if d.change_type == "D":
                continue

            filepath = d.b_path
            if not filepath:
                continue

            # Check if this file is supported by ASTParser
            ext = Path(filepath).suffix
            lang_name = self.parser.get_language_from_extension(ext)
            if not lang_name:
                continue

            # 1. Extract base content
            base_content: bytes | str = b""
            if d.change_type in ("M", "R", "C") and d.a_path:
                try:
                    # Retrieve blob from base commit
                    blob = base_commit.tree[d.a_path]
                    base_content = blob.data_stream.read()
                except Exception:
                    base_content = b""

            # 2. Extract target content
            target_content: bytes | str = b""
            if is_working_dir:
                file_full_path = self.repo_path / filepath
                if file_full_path.is_file():
                    try:
                        with open(file_full_path, "rb") as f:
                            target_content = f.read()
                    except Exception:
                        target_content = b""
            else:
                try:
                    blob = target_commit.tree[filepath]
                    target_content = blob.data_stream.read()
                except Exception:
                    target_content = b""

            # 3. Parse and extract dependencies
            base_deps: set[str] = set()
            if base_content:
                try:
                    base_ext = Path(d.a_path).suffix if d.a_path else ext
                    base_lang = self.parser.get_language_from_extension(base_ext) or "python"
                    base_ast = self.parser.parse_raw(base_content, base_ext)
                    for imp in base_ast.get("imports", []):
                        for dep in self._extract_dependencies(imp, base_lang):
                            base_deps.add(dep)
                except Exception:
                    pass

            target_deps: set[str] = set()
            if target_content:
                try:
                    target_lang = lang_name or "python"
                    target_ast = self.parser.parse_raw(target_content, ext)
                    for imp in target_ast.get("imports", []):
                        for dep in self._extract_dependencies(imp, target_lang):
                            target_deps.add(dep)
                except Exception:
                    pass

            # Compare dependency sets
            added = sorted(list(target_deps - base_deps))
            removed = sorted(list(base_deps - target_deps))

            if added or removed:
                drift_results[filepath] = {"added": added, "removed": removed}

        return drift_results

    def _extract_dependencies(self, import_stmt: str, lang: str) -> list[str]:
        """Extract module/package names from raw import statement."""
        import_stmt = import_stmt.strip()
        if not import_stmt:
            return []

        deps = []
        if lang == "python":
            if import_stmt.startswith("import "):
                parts = import_stmt[7:].split(",")
                for p in parts:
                    p = p.strip()
                    if " as " in p:
                        p = p.split(" as ")[0].strip()
                    if p:
                        deps.append(p)
            elif import_stmt.startswith("from "):
                match = re.match(r"^from\s+([\w\.]+)\s+import", import_stmt)
                if match:
                    deps.append(match.group(1))
                else:
                    parts = import_stmt.split("import")
                    if len(parts) > 0:
                        from_part = parts[0][5:].strip()
                        if from_part:
                            deps.append(from_part)
            else:
                deps.append(import_stmt)
        else:
            # JS/TS imports: e.g., import React from 'react';
            match = re.search(r"['\"`]([^'\"`]+)['\"`]", import_stmt)
            if match:
                deps.append(match.group(1))
            else:
                deps.append(import_stmt)

        return deps
