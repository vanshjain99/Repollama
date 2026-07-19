import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import docker
import docker.errors

from repollama.engines.sandbox import EnvironmentDetector, DockerSandbox

# --- EnvironmentDetector Tests ---

def test_detect_stack_javascript_node(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({
        "name": "test-project",
        "scripts": {
            "dev": "vite",
            "start": "node index.js",
            "test": "vitest"
        }
    }))
    
    detector = EnvironmentDetector(tmp_path)
    stack_info = detector.detect_stack()
    
    assert stack_info["stack"] == "Node/React"
    assert stack_info["language"] == "javascript"
    assert "dev" in stack_info["start_scripts"]
    assert "start" in stack_info["start_scripts"]
    assert stack_info["has_dockerfile"] is False
    assert stack_info["has_docker_compose"] is False


def test_detect_stack_python(tmp_path):
    req_txt = tmp_path / "requirements.txt"
    req_txt.write_text("fastapi==0.111.0\nuvicorn==0.30.0")
    
    detector = EnvironmentDetector(tmp_path)
    stack_info = detector.detect_stack()
    
    assert stack_info["stack"] == "Python"
    assert stack_info["language"] == "python"
    assert stack_info["has_dockerfile"] is False
    assert stack_info["has_docker_compose"] is False


def test_detect_stack_docker(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.11-slim")
    
    docker_compose = tmp_path / "docker-compose.yml"
    docker_compose.write_text("version: '3'")
    
    detector = EnvironmentDetector(tmp_path)
    stack_info = detector.detect_stack()
    
    assert stack_info["has_dockerfile"] is True
    assert stack_info["has_docker_compose"] is True


def test_detect_secrets_missing(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("""
    # This is a comment
    PORT=3000
    export DB_HOST=localhost
    SECRET_KEY=
    """)
    
    detector = EnvironmentDetector(tmp_path)
    secrets_info = detector.detect_secrets()
    
    assert "warning" in secrets_info
    assert "missing_keys" in secrets_info
    assert "PORT" in secrets_info["missing_keys"]
    assert "DB_HOST" in secrets_info["missing_keys"]
    assert "SECRET_KEY" in secrets_info["missing_keys"]


def test_detect_secrets_present(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("PORT=3000")
    env = tmp_path / ".env"
    env.write_text("PORT=3000")
    
    detector = EnvironmentDetector(tmp_path)
    secrets_info = detector.detect_secrets()
    
    assert secrets_info == {}


# --- DockerSandbox Tests ---

@patch("docker.from_env")
def test_docker_sandbox_init_success(mock_from_env):
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    
    sandbox = DockerSandbox()
    
    assert sandbox.is_available is True
    assert sandbox.client == mock_client
    mock_client.ping.assert_called_once()


@patch("docker.from_env")
def test_docker_sandbox_init_failure(mock_from_env):
    mock_from_env.side_effect = docker.errors.DockerException("Daemon not running")
    
    sandbox = DockerSandbox()
    
    assert sandbox.is_available is False
    assert sandbox.client is None


@patch("docker.from_env")
def test_start_sandbox_node(mock_from_env, tmp_path):
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "mock_container_123"
    mock_container.ports = {
        "5173/tcp": [{"HostIp": "0.0.0.0", "HostPort": "32768"}]
    }
    mock_client.containers.run.return_value = mock_container
    mock_from_env.return_value = mock_client
    
    sandbox = DockerSandbox()
    assert sandbox.is_available is True
    
    stack_info = {
        "stack": "Node/React",
        "language": "javascript",
        "start_scripts": ["dev"]
    }
    
    res = sandbox.start_sandbox(tmp_path, stack_info)
    
    assert res["container_id"] == "mock_container_123"
    assert res["host_port"] == 32768
    
    mock_client.containers.run.assert_called_once()
    kwargs = mock_client.containers.run.call_args[1]
    assert kwargs["image"] == "node:20-alpine"
    assert "npm run dev" in kwargs["command"]
    assert kwargs["detach"] is True
    assert kwargs["working_dir"] == "/app"
    assert str(Path(tmp_path).resolve()) in kwargs["volumes"]


@patch("docker.from_env")
def test_start_sandbox_python(mock_from_env, tmp_path):
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "mock_container_456"
    mock_container.ports = {
        "8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "49152"}]
    }
    mock_client.containers.run.return_value = mock_container
    mock_from_env.return_value = mock_client
    
    (tmp_path / "requirements.txt").write_text("fastapi")
    (tmp_path / "main.py").write_text("print('hello')")
    
    sandbox = DockerSandbox()
    stack_info = {
        "stack": "Python",
        "language": "python",
        "start_scripts": []
    }
    
    res = sandbox.start_sandbox(tmp_path, stack_info)
    
    assert res["container_id"] == "mock_container_456"
    assert res["host_port"] == 49152
    
    mock_client.containers.run.assert_called_once()
    kwargs = mock_client.containers.run.call_args[1]
    assert kwargs["image"] == "python:3.11-slim"
    assert "pip install -r requirements.txt" in kwargs["command"]
    assert "python main.py" in kwargs["command"]


@patch("docker.from_env")
def test_stop_sandbox(mock_from_env):
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_from_env.return_value = mock_client
    
    sandbox = DockerSandbox()
    sandbox._active_containers.append("mock_container_123")
    
    sandbox.stop_sandbox("mock_container_123")
    
    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once_with(force=True)
    assert "mock_container_123" not in sandbox._active_containers
