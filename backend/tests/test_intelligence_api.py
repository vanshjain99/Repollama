import pytest
from fastapi.testclient import TestClient
from repollama.main import app

client = TestClient(app)


def test_get_debt_report():
    response = client.get("/api/v1/intelligence/debt")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data
    assert isinstance(data["results"], list)


def test_get_audit_reports():
    response = client.get("/api/v1/intelligence/audits")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "security" in data
    assert "performance" in data
    assert isinstance(data["security"], list)
    assert isinstance(data["performance"], list)
