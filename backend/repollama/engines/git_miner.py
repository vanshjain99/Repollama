from __future__ import annotations
from pathlib import Path
from typing import Any
from git import Repo
from git.exc import InvalidGitRepositoryError as GitPythonInvalidGitRepositoryError, NoSuchPathError


class InvalidGitRepositoryError(ValueError):
    """Exception raised when the path is not a valid Git repository."""
    pass


class GitMiner:
    """GitMiner engine to mine git metadata, commit history, and file churn metrics."""

    def __init__(self, repo_path: str | Path) -> None:
        """Initialize GitMiner with repository path and validate that it is a valid Git repository.

        Args:
            repo_path (str | Path): Path to the target Git repository.

        Raises:
            InvalidGitRepositoryError: If the path is not a valid Git repository or does not exist.
        """
        self.repo_path = Path(repo_path).resolve()
        try:
            self.repo = Repo(self.repo_path)
        except (GitPythonInvalidGitRepositoryError, NoSuchPathError) as e:
            raise InvalidGitRepositoryError(
                f"Path '{repo_path}' is not a valid Git repository."
            ) from e

    def get_repository_metadata(self) -> dict[str, Any]:
        """Extract high-level metadata about the repository.

        Returns:
            dict[str, Any]: A dictionary containing:
                - active_branch: Name of the currently active branch.
                - local_branches: List of local branch names.
                - commit_count: Total commit count on the current branch/HEAD.
        """
        local_branches = [b.name for b in self.repo.branches]

        active_branch = "None"
        commit_count = 0

        if self.repo.head.is_valid():
            try:
                active_branch = self.repo.active_branch.name
            except TypeError:
                active_branch = "HEAD (detached)"
            except Exception:
                active_branch = "unknown"

            try:
                # iter_commits returns commits reachable from HEAD
                commit_count = sum(1 for _ in self.repo.iter_commits())
            except Exception:
                commit_count = 0

        return {
            "active_branch": active_branch,
            "local_branches": local_branches,
            "commit_count": commit_count,
        }

    def get_commit_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent commit history up to the specified limit.

        Args:
            limit (int): Maximum number of commits to retrieve. Defaults to 50.

        Returns:
            list[dict[str, Any]]: A list of dictionaries representing commits, sorted from newest to oldest.
                Each dictionary contains:
                - hash: Short commit hash (7 characters).
                - author: Name of the commit author.
                - date: Authored date in ISO format.
                - message: First line (summary) of the commit message.
                - files_changed: List of file paths changed/added/deleted in this commit.
        """
        if not self.repo.head.is_valid():
            return []

        try:
            commits = list(self.repo.iter_commits(max_count=limit))
        except Exception:
            return []

        history = []
        for commit in commits:
            files_changed = []
            try:
                if commit.parents:
                    diffs = commit.parents[0].diff(commit)
                    for d in diffs:
                        path = d.b_path or d.a_path
                        if path:
                            files_changed.append(path)
                else:
                    # Initial commit: all files in the tree are considered changed
                    for item in commit.tree.traverse():
                        item_type = getattr(item, "type", None)
                        item_path = getattr(item, "path", None)
                        if item_type == "blob" and isinstance(item_path, str):
                            files_changed.append(item_path)

            except Exception:
                pass

            history.append({
                "hash": commit.hexsha[:7],
                "author": commit.author.name if commit.author else "Unknown",
                "date": commit.authored_datetime.isoformat() if commit.authored_datetime else "",
                "message": commit.summary or "",
                "files_changed": files_changed,
            })

        return history

    def get_file_churn(self, limit: int = 100) -> dict[str, int]:
        """Calculate file churn (number of times each file has been modified) across commit history.

        Args:
            limit (int): The maximum number of files to return in the churn map. Defaults to 100.

        Returns:
            dict[str, int]: A dictionary mapping file paths to their modification count,
                sorted from most modified to least modified.
        """
        if not self.repo.head.is_valid():
            return {}

        churn: dict[str, int] = {}
        try:
            # Iterate through all commits reachable from HEAD
            for commit in self.repo.iter_commits():
                if commit.parents:
                    diffs = commit.parents[0].diff(commit)
                    for d in diffs:
                        path = d.b_path or d.a_path
                        if path:
                            churn[path] = churn.get(path, 0) + 1
                else:
                    # Initial commit
                    for item in commit.tree.traverse():
                        item_type = getattr(item, "type", None)
                        item_path = getattr(item, "path", None)
                        if item_type == "blob" and isinstance(item_path, str):
                            churn[item_path] = churn.get(item_path, 0) + 1

        except Exception:
            pass

        sorted_churn = sorted(churn.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_churn[:limit])
