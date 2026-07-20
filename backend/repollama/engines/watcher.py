from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Callable
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

class RepoEventHandler(FileSystemEventHandler):
    """Event handler that filters file system events and runs a callback for supported files."""

    def __init__(
        self,
        repo_path: str | Path,
        callback: Callable[[str, str], None],
    ) -> None:
        """Initialize event handler.

        Args:
            repo_path: Path to the root repository being watched.
            callback: Callback function invoked with (file_path, event_type).
        """
        super().__init__()
        self.repo_path = Path(repo_path).resolve()
        self.callback = callback
        self.exclude_dirs = {
            ".git",
            "node_modules",
            "venv",
            ".venv",
            "dist",
            "__pycache__",
            ".repollama_data",
            ".pytest_cache",
            ".mypy_cache",
        }
        self.supported_extensions = {".py", ".js", ".jsx", ".ts", ".tsx"}

    def is_supported_file(self, path_str: str) -> bool:
        """Check if the given path is a supported source code file and not excluded."""
        path = Path(path_str).resolve()
        if path.exists() and path.is_dir():
            return False

        try:
            rel_path = path.relative_to(self.repo_path)
            if any(part in self.exclude_dirs for part in rel_path.parts):
                return False
        except ValueError:
            # Fallback if path is not relative to repo_path
            if any(part in self.exclude_dirs for part in path.parts):
                return False

        return path.suffix.lower() in self.supported_extensions

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory and self.is_supported_file(event.src_path):
            self.callback(event.src_path, "modified")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory and self.is_supported_file(event.src_path):
            self.callback(event.src_path, "created")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if not event.is_directory and self.is_supported_file(event.src_path):
            self.callback(event.src_path, "deleted")


class RepoWatcher:
    """Manages the file system observer to watch a directory for changes."""

    def __init__(
        self,
        repo_path: str | Path,
        callback: Callable[[str, str], None],
    ) -> None:
        """Initialize the watcher.

        Args:
            repo_path: Path of the repository to monitor.
            callback: Callback triggered on file changes.
        """
        self.repo_path = Path(repo_path).resolve()
        self.callback = callback
        self.observer: Observer | None = None

    def start(self) -> None:
        """Start the background file system observer."""
        if self.observer is not None:
            return
        self.observer = Observer()
        handler = RepoEventHandler(self.repo_path, self.callback)
        self.observer.schedule(handler, path=str(self.repo_path), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """Stop the background observer and join the thread."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
