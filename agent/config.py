"""Settings module — loads all configuration from environment via pydantic-settings."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables or .env file."""

    groq_api_key: str
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str = Field(
        default="https://us.cloud.langfuse.com",
        validation_alias=AliasChoices("langfuse_host", "langfuse_base_url"),
    )
    groq_model: str = "llama-3.3-70b-versatile"
    data_dir: str = "./data"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
