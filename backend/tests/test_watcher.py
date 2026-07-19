from __future__ import annotations
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from watchdog.events import (
    FileModifiedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    DirModifiedEvent,
)
from repollama.engines.watcher import RepoEventHandler, RepoWatcher


def test_repo_event_handler_filtering():
    repo_path = Path("/workspace/myrepo")
    callback = Mock()
    handler = RepoEventHandler(repo_path, callback)

    # 1. Supported file modified
    event = FileModifiedEvent("/workspace/myrepo/src/main.py")
    handler.on_modified(event)
    callback.assert_called_once_with("/workspace/myrepo/src/main.py", "modified")
    callback.reset_mock()

    # 2. Unsupported file modified (e.g. .txt)
    event = FileModifiedEvent("/workspace/myrepo/src/readme.txt")
    handler.on_modified(event)
    callback.assert_not_called()
    callback.reset_mock()

    # 3. Excluded directory file modified (e.g. node_modules)
    event = FileModifiedEvent("/workspace/myrepo/node_modules/lodash/index.js")
    handler.on_modified(event)
    callback.assert_not_called()
    callback.reset_mock()

    # 4. Git directory file modified
    event = FileModifiedEvent("/workspace/myrepo/.git/config")
    handler.on_modified(event)
    callback.assert_not_called()
    callback.reset_mock()

    # 5. Directory event itself should be ignored
    dir_event = DirModifiedEvent("/workspace/myrepo/src")
    handler.on_modified(dir_event)
    callback.assert_not_called()
    callback.reset_mock()


def test_repo_event_handler_created_and_deleted():
    repo_path = Path("/workspace/myrepo")
    callback = Mock()
    handler = RepoEventHandler(repo_path, callback)

    # Created event
    event_created = FileCreatedEvent("/workspace/myrepo/src/new_file.ts")
    handler.on_created(event_created)
    callback.assert_called_once_with("/workspace/myrepo/src/new_file.ts", "created")
    callback.reset_mock()

    # Deleted event
    event_deleted = FileDeletedEvent("/workspace/myrepo/src/old_file.tsx")
    handler.on_deleted(event_deleted)
    callback.assert_called_once_with("/workspace/myrepo/src/old_file.tsx", "deleted")
    callback.reset_mock()


def test_repo_watcher_lifecycle():
    repo_path = Path("/workspace/myrepo")
    callback = Mock()
    watcher = RepoWatcher(repo_path, callback)

    with patch("repollama.engines.watcher.Observer") as mock_observer_class:
        mock_observer = mock_observer_class.return_value

        # Start the watcher
        watcher.start()
        mock_observer_class.assert_called_once()
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()

        # Stop the watcher
        watcher.stop()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
        assert watcher.observer is None
