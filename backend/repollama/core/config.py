from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for Repollama backend core."""

    # Base URL for the local Ollama instance
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Default model to use for local LLM operations
    DEFAULT_MODEL: str = "qwen2.5-coder"

    # Host and port configuration for running the FastAPI application
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_prefix="REPOLLAMA_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
