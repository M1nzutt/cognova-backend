from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read backend configuration from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    cors_origins: list[str] = []
