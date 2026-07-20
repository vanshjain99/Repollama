from __future__ import annotations
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from repollama.main import app

client = TestClient(app)


def test_audit_log_endpoint_missing() -> None:
    with patch("repollama.main.Path.exists", return_value=False):
        response = client.get("/api/v1/governance/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["exists"] is False
        assert data["lines"] == []


@patch("repollama.engines.ci_gatekeeper.CIGatekeeper.evaluate_pr", new_callable=AsyncMock)
def test_ci_check_endpoint_pass(mock_evaluate: AsyncMock) -> None:
    mock_evaluate.return_value = {
        "passed": True,
        "drift": {},
        "highest_debt_score": 35,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        payload = {
            "path": tmpdir,
            "base_ref": "HEAD~1",
            "target_ref": "HEAD",
            "role": "developer"
        }
        response = client.post("/api/v1/governance/ci-check", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["passed"] is True
        assert data["bypassed"] is False
        assert data["highest_debt_score"] == 35


@patch("repollama.engines.ci_gatekeeper.CIGatekeeper.evaluate_pr", new_callable=AsyncMock)
def test_ci_check_endpoint_architect_bypass(mock_evaluate: AsyncMock) -> None:
    mock_evaluate.return_value = {
        "passed": False,
        "drift": {"src/app.py": {"added": ["requests"], "removed": []}},
        "highest_debt_score": 45,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        payload = {
            "path": tmpdir,
            "base_ref": "HEAD~1",
            "target_ref": "HEAD",
            "role": "architect"
        }
        response = client.post("/api/v1/governance/ci-check", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["passed"] is True
        assert data["bypassed"] is True
        assert data["has_drift"] is True
