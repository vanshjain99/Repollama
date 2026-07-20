from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from repollama.main import app

def test_get_sandbox_status():
    client = TestClient(app)
    with patch("repollama.engines.sandbox.DockerSandbox") as MockDocker:
        mock_instance = MagicMock()
        mock_instance.is_available = True
        MockDocker.return_value = mock_instance

        response = client.get("/api/v1/sandbox/status")
        assert response.status_code == 200
        data = response.json()
        assert "docker_available" in data
        assert "status" in data

def test_start_sandbox():
    client = TestClient(app)
    with patch("repollama.engines.sandbox.DockerSandbox") as MockDocker, \
         patch("repollama.engines.sandbox.EnvironmentDetector") as MockDetector:
        
        mock_sandbox = MagicMock()
        mock_sandbox.is_available = True
        mock_sandbox.start_sandbox.return_value = {
            "container_id": "mock_container_123",
            "host_port": 5173
        }
        MockDocker.return_value = mock_sandbox

        mock_det = MagicMock()
        mock_det.detect_stack.return_value = {
            "stack": "Node/React",
            "start_scripts": ["dev"],
            "has_dockerfile": False,
            "has_docker_compose": False,
            "language": "javascript"
        }
        mock_det.detect_secrets.return_value = {}
        MockDetector.return_value = mock_det

        response = client.post("/api/v1/sandbox/start", json={"path": "."})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["container_id"] == "mock_container_123"
        assert data["host_port"] == 5173

def test_stop_sandbox():
    client = TestClient(app)
    with patch("repollama.engines.sandbox.DockerSandbox") as MockDocker:
        mock_sandbox = MagicMock()
        mock_sandbox.is_available = True
        MockDocker.return_value = mock_sandbox

        response = client.post("/api/v1/sandbox/stop", json={"container_id": "mock_container_123"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

def test_list_workflows():
    client = TestClient(app)
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    data = response.json()
    assert "workflows" in data
    assert len(data["workflows"]) > 0
    assert "diagram" in data["workflows"][0]

def test_trace_workflow():
    client = TestClient(app)
    response = client.post("/api/v1/workflows/trace", json={"url": "http://localhost:8000", "action": "Login"})
    assert response.status_code == 200
    data = response.json()
    assert "diagram" in data
    assert "sequenceDiagram" in data["diagram"]

def test_list_and_stream_videos():
    client = TestClient(app)
    response = client.get("/api/v1/videos")
    assert response.status_code == 200
    data = response.json()
    assert "videos" in data
