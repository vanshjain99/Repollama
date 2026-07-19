from __future__ import annotations
import atexit
import json
from pathlib import Path
from typing import Any

import docker
import docker.errors

class EnvironmentDetector:
    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()

    def detect_stack(self) -> dict[str, Any]:
        """Detect the development stack, start scripts, and Docker configuration of the repository."""
        stack_info = {
            "stack": "unknown",
            "start_scripts": [],
            "has_dockerfile": False,
            "has_docker_compose": False,
            "language": "unknown",
        }

        # Check Node/React
        pkg_json_path = self.repo_path / "package.json"
        if pkg_json_path.is_file():
            stack_info["stack"] = "Node/React"
            stack_info["language"] = "javascript"
            try:
                with open(pkg_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scripts = data.get("scripts", {})
                    # Look for start scripts (e.g., dev, start)
                    for script_name in ["dev", "start"]:
                        if script_name in scripts:
                            stack_info["start_scripts"].append(script_name)
            except Exception:
                pass

        # Check Python
        req_txt_path = self.repo_path / "requirements.txt"
        pyproject_path = self.repo_path / "pyproject.toml"
        if req_txt_path.is_file() or pyproject_path.is_file():
            # Standard Python stack
            stack_info["stack"] = "Python"
            stack_info["language"] = "python"

        # Check Dockerfile & docker-compose
        dockerfile_path = self.repo_path / "Dockerfile"
        if dockerfile_path.is_file():
            stack_info["has_dockerfile"] = True

        for name in ["docker-compose.yml", "docker-compose.yaml"]:
            if (self.repo_path / name).is_file():
                stack_info["has_docker_compose"] = True
                break

        return stack_info

    def detect_secrets(self) -> dict[str, Any]:
        """Detect if required .env files are missing based on templates."""
        dotenv_path = self.repo_path / ".env"
        if dotenv_path.is_file():
            return {}  # No missing configuration

        template_files = [".env.example", ".env.template"]
        template_path = None
        for name in template_files:
            if (self.repo_path / name).is_file():
                template_path = self.repo_path / name
                break

        if not template_path:
            return {}

        missing_keys = []
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        parts = line.split("=", 1)
                        key = parts[0].strip()
                        if key.startswith("export "):
                            key = key[len("export "):].strip()
                        if key:
                            missing_keys.append(key)
        except Exception:
            pass

        if missing_keys:
            return {
                "warning": f"Missing .env configuration file (based on {template_path.name})",
                "missing_keys": missing_keys,
            }
        return {}


class DockerSandbox:
    def __init__(self) -> None:
        self.client = None
        self.is_available = False
        self._active_containers: list[str] = []

        try:
            self.client = docker.from_env()
            self.client.ping()
            self.is_available = True
        except Exception:
            self.client = None
            self.is_available = False

        atexit.register(self._cleanup_active_containers)

    def _cleanup_active_containers(self) -> None:
        """Clean up active containers started by this instance on exit."""
        for cid in list(self._active_containers):
            try:
                self.stop_sandbox(cid)
            except Exception:
                pass

    def start_sandbox(self, repo_path: str | Path, stack_info: dict[str, Any]) -> dict[str, Any]:
        """Start a Docker container for the repository based on stack info.

        Returns:
            dict: Contains 'container_id' and 'host_port'.
        """
        if not self.is_available or not self.client:
            raise RuntimeError("Docker daemon is not running or available.")

        repo_path_abs = str(Path(repo_path).resolve())

        # Select base image and startup command
        stack = stack_info.get("stack", "unknown")
        if stack == "Node/React":
            image = "node:20-alpine"
            start_scripts = stack_info.get("start_scripts", [])
            if "dev" in start_scripts:
                cmd_str = "npm install && npm run dev"
            elif "start" in start_scripts:
                cmd_str = "npm install && npm run start"
            else:
                cmd_str = "npm install && npm start"
            command = f"sh -c '{cmd_str}'"
        elif stack == "Python":
            image = "python:3.11-slim"
            cmd_parts = []
            repo_p = Path(repo_path)
            if (repo_p / "requirements.txt").is_file():
                cmd_parts.append("pip install -r requirements.txt")
            elif (repo_p / "pyproject.toml").is_file():
                cmd_parts.append("pip install .")

            if (repo_p / "main.py").is_file():
                cmd_parts.append("python main.py")
            elif (repo_p / "app.py").is_file():
                cmd_parts.append("python app.py")
            else:
                cmd_parts.append("tail -f /dev/null")

            command = f"sh -c '{' && '.join(cmd_parts)}'"
        else:
            image = "alpine:latest"
            command = "tail -f /dev/null"

        ports = {
            "3000/tcp": None,
            "5173/tcp": None,
            "8000/tcp": None,
        }

        volumes = {
            repo_path_abs: {
                "bind": "/app",
                "mode": "rw",
            }
        }

        try:
            container = self.client.containers.run(
                image=image,
                command=command,
                detach=True,
                volumes=volumes,
                ports=ports,
                working_dir="/app",
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start Docker container: {e}") from e

        self._active_containers.append(container.id)

        # Get mapped host port
        host_port = None
        try:
            container.reload()
            ports_info = container.ports or {}
            target_ports = []
            if stack == "Node/React":
                target_ports = ["5173/tcp", "3000/tcp"]
            elif stack == "Python":
                target_ports = ["8000/tcp"]

            for tp in target_ports:
                if tp in ports_info and ports_info[tp]:
                    host_port = int(ports_info[tp][0]["HostPort"])
                    break

            if host_port is None:
                for port_name, mappings in ports_info.items():
                    if mappings:
                        host_port = int(mappings[0]["HostPort"])
                        break
        except Exception:
            pass

        return {
            "container_id": container.id,
            "host_port": host_port,
        }

    def stop_sandbox(self, container_id: str) -> None:
        """Stop and force remove the container."""
        if not self.is_available or not self.client:
            raise RuntimeError("Docker daemon is not running or available.")

        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
        except Exception:
            pass

        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
        except Exception:
            pass

        if container_id in self._active_containers:
            self._active_containers.remove(container_id)
