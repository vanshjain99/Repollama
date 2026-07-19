from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
from repollama.engines.drift_engine import DriftDetector
from repollama.engines.ast_parser import ASTParser


def test_ast_parser_parse_raw():
    parser = ASTParser()
    # Test Python parsing
    code_py = "import os\nfrom sys import path"
    metadata_py = parser.parse_raw(code_py, ".py")
    assert metadata_py["language"] == "python"
    assert "import os" in metadata_py["imports"]
    assert "from sys import path" in metadata_py["imports"]

    # Test TS/JS parsing
    code_ts = "import React from 'react';\nimport { Button } from '@mui/material';"
    metadata_ts = parser.parse_raw(code_ts, ".tsx")
    assert metadata_ts["language"] == "tsx"
    assert len(metadata_ts["imports"]) == 2


@patch("repollama.engines.drift_engine.Repo")
def test_drift_detector_detect_drift(mock_repo_class):
    # Setup mock repo
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo

    detector = DriftDetector("/dummy/path")

    # Mock commits
    mock_base_commit = MagicMock()
    mock_target_commit = MagicMock()

    mock_repo.commit.side_effect = lambda ref: mock_base_commit if "HEAD~1" in ref else mock_target_commit

    # Mock Diff object
    mock_diff = MagicMock()
    mock_diff.change_type = "M"
    mock_diff.a_path = "src/api.py"
    mock_diff.b_path = "src/api.py"

    mock_base_commit.diff.return_value = [mock_diff]

    # Mock file contents
    base_file_content = b"import os\nfrom sys import path"
    target_file_content = b"import os\nfrom sys import path\nimport sqlalchemy.orm"

    # Mock blobs inside commit tree
    mock_base_blob = MagicMock()
    mock_base_blob.data_stream.read.return_value = base_file_content

    mock_target_blob = MagicMock()
    mock_target_blob.data_stream.read.return_value = target_file_content

    # Mock base_commit.tree[a_path] and target_commit.tree[b_path]
    mock_base_commit.tree.__getitem__.side_effect = lambda key: mock_base_blob if key == "src/api.py" else KeyError()
    mock_target_commit.tree.__getitem__.side_effect = lambda key: mock_target_blob if key == "src/api.py" else KeyError()

    # Run detection
    results = detector.detect_drift(base_ref="HEAD~1", target_ref="HEAD")

    # Assert correct output format and parsed imports
    assert "src/api.py" in results
    assert results["src/api.py"]["added"] == ["sqlalchemy.orm"]
    assert results["src/api.py"]["removed"] == []


@patch("repollama.engines.drift_engine.Repo")
def test_drift_detector_added_file(mock_repo_class):
    # Setup mock repo
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo

    detector = DriftDetector("/dummy/path")

    # Mock commits
    mock_base_commit = MagicMock()
    mock_target_commit = MagicMock()

    mock_repo.commit.side_effect = lambda ref: mock_base_commit if "HEAD~1" in ref else mock_target_commit

    # Mock Diff object for an Added file
    mock_diff = MagicMock()
    mock_diff.change_type = "A"
    mock_diff.a_path = None
    mock_diff.b_path = "src/new_helper.ts"

    mock_base_commit.diff.return_value = [mock_diff]

    # Target content
    target_file_content = b"import { useState } from 'react';"

    # Mock target blob
    mock_target_blob = MagicMock()
    mock_target_blob.data_stream.read.return_value = target_file_content

    mock_target_commit.tree.__getitem__.side_effect = lambda key: mock_target_blob if key == "src/new_helper.ts" else KeyError()

    # Run detection
    results = detector.detect_drift(base_ref="HEAD~1", target_ref="HEAD")

    # Assert correct output
    assert "src/new_helper.ts" in results
    assert results["src/new_helper.ts"]["added"] == ["react"]
    assert results["src/new_helper.ts"]["removed"] == []


@patch("repollama.engines.drift_engine.Repo")
def test_drift_detector_deleted_file(mock_repo_class):
    # Setup mock repo
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo

    detector = DriftDetector("/dummy/path")

    # Mock commits
    mock_base_commit = MagicMock()
    mock_target_commit = MagicMock()

    mock_repo.commit.side_effect = lambda ref: mock_base_commit if "HEAD~1" in ref else mock_target_commit

    # Mock Diff object for a Deleted file (change_type='D')
    mock_diff = MagicMock()
    mock_diff.change_type = "D"
    mock_diff.a_path = "src/deleted.py"
    mock_diff.b_path = None

    mock_base_commit.diff.return_value = [mock_diff]

    # Run detection
    results = detector.detect_drift(base_ref="HEAD~1", target_ref="HEAD")

    # Deleted files should be skipped, so no drift results
    assert results == {}
