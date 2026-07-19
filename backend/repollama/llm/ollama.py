from __future__ import annotations
import httpx

# Fallback URL tried when the primary base_url fails to connect.
# Handles environments where "localhost" resolves differently (e.g. inside Tauri).
_FALLBACK_URL = "http://127.0.0.1:11434"


class OllamaManager:
    """Connection manager for interacting with the local Ollama API."""

    def __init__(self, base_url: str) -> None:
        """Initialize the manager with the Ollama base URL.

        Args:
            base_url: The absolute base URL of the Ollama server.
        """
        self._base_url = base_url.rstrip("/")

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._base_url = value.rstrip("/")

    async def ping_server(self) -> bool:
        """Pings the Ollama server to verify it is reachable.

        Returns:
            bool: True if reachable, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                # Ollama's base URL returns a text message indicating it is running
                response = await client.get(self.base_url)
                return response.status_code == 200
        except (httpx.ConnectError, httpx.HTTPError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str]:
        """Lists names of all locally available Ollama models.

        Returns:
            list[str]: Installed model names.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    return [m["name"] for m in models]
                return []
        except (httpx.ConnectError, httpx.HTTPError, httpx.TimeoutException):
            return []

    async def pull_model(self, model_name: str) -> None:
        """Pulls a model from the Ollama library.

        Handles the streaming progress internally and blocks asynchronously until completed.

        Args:
            model_name: The name of the model to pull.
        """
        try:
            # Set timeout to None as model downloading can take minutes
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                ) as response:
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(
                            f"Failed to pull model, status: {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    async for chunk in response.aiter_text():
                        # In the future, progress can be piped to an SSE stream
                        pass
        except (httpx.ConnectError, httpx.HTTPError) as e:
            raise RuntimeError(
                f"Ollama connection error during model pull: {e}"
            ) from e

    async def generate(self, prompt: str, model: str, timeout: float | None = 300.0) -> str:
        """Basic text generation using the Ollama API.

        Automatically retries on the 127.0.0.1 fallback URL if the primary
        address fails with a connection error (handles localhost DNS quirks
        inside the Tauri desktop runtime).

        Args:
            prompt: Prompt string.
            model: The name of the model to generate with.
            timeout: Request timeout in seconds. Defaults to 300.0.

        Returns:
            str: Generated text.
        """
        urls_to_try = [self._base_url]
        if self._base_url != _FALLBACK_URL:
            urls_to_try.append(_FALLBACK_URL)

        last_error: Exception | None = None
        for url in urls_to_try:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{url}/api/generate",
                        json={"model": model, "prompt": prompt, "stream": False},
                    )
                    if response.status_code == 200:
                        return response.json().get("response", "")
                    else:
                        raise httpx.HTTPStatusError(
                            f"Ollama generation failed (status {response.status_code}) at {url}",
                            request=response.request,
                            response=response,
                        )
            except httpx.ConnectError as e:
                last_error = e
                continue  # Try next URL
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                raise RuntimeError(
                    f"Ollama HTTP/timeout error at {url}: {e}"
                ) from e

        raise RuntimeError(
            f"Cannot connect to Ollama at {self._base_url} or fallback {_FALLBACK_URL}. "
            "Ensure Ollama is running: `ollama serve`."
        ) from last_error
