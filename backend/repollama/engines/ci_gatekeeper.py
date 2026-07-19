from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any
from git import Repo

from repollama.engines.drift_engine import DriftDetector
from repollama.engines.debt_evaluator import DebtEvaluator
from repollama.engines.git_miner import GitMiner
from repollama.engines.ast_parser import ASTParser
from repollama.engines.graph_builder import KnowledgeGraphBuilder


class CIGatekeeper:
    """CI/CD Gatekeeper for evaluating PR architecture drift and technical debt."""

    async def evaluate_pr(
        self, repo_path: str | Path, base_ref: str = "HEAD~1", target_ref: str = "HEAD"
    ) -> dict[str, Any]:
        """Evaluate a repository pull request (between base_ref and target_ref) for quality gates.

        Args:
            repo_path (str | Path): Path to the Git repository.
            base_ref (str): Base git reference (e.g. branch or commit SHA).
            target_ref (str): Target git reference (e.g. branch, commit SHA, or 'working_dir').

        Returns:
            dict[str, Any]: Report containing 'passed', 'drift', and 'highest_debt_score'.
        """
        resolved_path = Path(repo_path).resolve()
        if not resolved_path.exists() or not resolved_path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist or is not a directory: {repo_path}")

        # 1. Evaluate architectural drift using DriftDetector
        detector = DriftDetector(resolved_path)
        drift_report = detector.detect_drift(base_ref=base_ref, target_ref=target_ref)

        # Check for ANY added dependencies
        has_drift = False
        for changes in drift_report.values():
            if changes.get("added"):
                has_drift = True
                break

        # 2. Identify modified/added files in the PR via git diff
        repo = Repo(resolved_path)
        try:
            base_commit = repo.commit(base_ref)
        except Exception as e:
            raise ValueError(f"Could not resolve base reference '{base_ref}': {e}")

        # Determine target ref or working dir
        is_working_dir = False
        if target_ref is None:
            is_working_dir = True
        elif isinstance(target_ref, str):
            ref_lower = target_ref.lower()
            if ref_lower in ("working_dir", "working_tree", "worktree", "working"):
                is_working_dir = True

        if is_working_dir:
            diffs = base_commit.diff(None)
        else:
            try:
                target_commit = repo.commit(target_ref)
                diffs = base_commit.diff(target_commit)
            except Exception as e:
                raise ValueError(f"Could not resolve target reference '{target_ref}': {e}")

        modified_files = set()
        for d in diffs:
            if d.change_type != "D" and d.b_path:
                modified_files.add(d.b_path)

        # 3. Evaluate Technical Debt
        file_churn: dict[str, int] = {}
        try:
            miner = GitMiner(resolved_path)
            file_churn = miner.get_file_churn(limit=99999)
        except Exception:
            pass

        parser = ASTParser()
        graph_builder = KnowledgeGraphBuilder()

        # Directories to exclude from AST/debt evaluation
        exclude_dirs = {
            ".git",
            "node_modules",
            "venv",
            ".venv",
            "__pycache__",
            ".repollama_data",
            ".pytest_cache",
            ".mypy_cache",
        }
        supported_extensions = {".py", ".js", ".jsx", ".ts", ".tsx"}

        # Walk repo to build knowledge graph
        for path_obj in resolved_path.rglob("*"):
            if not path_obj.is_file():
                continue

            relative_path = path_obj.relative_to(resolved_path)
            if any(part in exclude_dirs for part in relative_path.parts):
                continue

            if path_obj.suffix.lower() not in supported_extensions:
                continue

            file_path_str = str(relative_path)
            try:
                ast_meta = parser.parse_file(path_obj)
                graph_builder.add_file_node(file_path_str, {"language": ast_meta.language})

                for cls in ast_meta.classes:
                    graph_builder.add_code_node(cls.name, "class", file_path_str)

                for func in ast_meta.functions:
                    graph_builder.add_code_node(func.name, "function", file_path_str)

                for imp in ast_meta.imports:
                    graph_builder.add_import_edge(file_path_str, imp)
            except Exception:
                pass

        evaluator = DebtEvaluator(graph_builder.graph, file_churn)
        debt_results = await evaluator.evaluate()

        # Find highest debt score among modified files
        highest_debt_score = 0
        has_high_debt = False
        for item in debt_results:
            file_name = item["file"]
            if file_name in modified_files:
                score = item["score"]
                if score > highest_debt_score:
                    highest_debt_score = score
                if score > 80:
                    has_high_debt = True

        passed = not has_drift and not has_high_debt

        return {
            "passed": passed,
            "drift": drift_report,
            "highest_debt_score": highest_debt_score,
        }
