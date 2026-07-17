from pathlib import Path
import pytest
from git import Repo
from repollama.engines.git_miner import GitMiner, InvalidGitRepositoryError


def test_invalid_git_repository(tmp_path):
    # Path exists but not a git repo
    with pytest.raises(InvalidGitRepositoryError):
        GitMiner(tmp_path)

    # Path doesn't exist
    with pytest.raises(InvalidGitRepositoryError):
        GitMiner(tmp_path / "nonexistent")


def test_git_miner_empty_repo(tmp_path):
    repo_dir = tmp_path / "empty_repo"
    repo_dir.mkdir()
    Repo.init(repo_dir)

    miner = GitMiner(repo_dir)
    metadata = miner.get_repository_metadata()

    assert metadata["commit_count"] == 0
    assert miner.get_commit_history() == []
    assert miner.get_file_churn() == {}


def test_git_miner_with_commits(tmp_path):
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)

    # Configure user name and email in the test repository
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test User")
        cw.set_value("user", "email", "test@example.com")

    # Create file A
    file_a = repo_dir / "file_a.txt"
    file_a.write_text("Hello World")

    # First commit (initial commit)
    repo.index.add(["file_a.txt"])
    repo.index.commit("Initial commit")

    # Create file B and edit file A
    file_b = repo_dir / "file_b.txt"
    file_b.write_text("Hello B")
    file_a.write_text("Hello World Edited")

    # Second commit
    repo.index.add(["file_a.txt", "file_b.txt"])
    repo.index.commit("Second commit: Add file_b and update file_a")

    # Edit file B
    file_b.write_text("Hello B Edited")

    # Third commit
    repo.index.add(["file_b.txt"])
    repo.index.commit("Third commit: Update file_b")

    # Run GitMiner
    miner = GitMiner(repo_dir)

    # Test Repository Metadata
    metadata = miner.get_repository_metadata()
    assert metadata["active_branch"] in ("master", "main")
    assert metadata["commit_count"] == 3
    assert len(metadata["local_branches"]) == 1

    # Test Commit History
    history = miner.get_commit_history(limit=5)
    assert len(history) == 3

    # Commits are sorted newest to oldest
    assert history[0]["message"] == "Third commit: Update file_b"
    assert "file_b.txt" in history[0]["files_changed"]
    assert len(history[0]["files_changed"]) == 1

    assert history[1]["message"] == "Second commit: Add file_b and update file_a"
    assert "file_a.txt" in history[1]["files_changed"]
    assert "file_b.txt" in history[1]["files_changed"]
    assert len(history[1]["files_changed"]) == 2

    assert history[2]["message"] == "Initial commit"
    assert "file_a.txt" in history[2]["files_changed"]

    # Test File Churn
    churn = miner.get_file_churn()
    assert churn["file_a.txt"] == 2
    assert churn["file_b.txt"] == 2
