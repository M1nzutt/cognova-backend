from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    """Read backend configuration from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    cors_allowed_origins: list[str] = []
    database_url: SecretStr
    jwt_secret: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=15)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=90)
    cookie_secure: bool = True
    cookie_samesite: Literal["lax"] = "lax"
    auth_rate_limit: int = Field(default=20, ge=1)
    auth_rate_window_seconds: int = Field(default=60, ge=1, le=3600)
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parts = urlsplit(origin)
            if (
                parts.scheme not in ("http", "https")
                or not parts.hostname
                or "*" in origin
                or parts.path
                or parts.query
                or parts.fragment
                or parts.username
                or parts.password
            ):
                raise ValueError("CORS requires explicit HTTP(S) origins")
        return origins

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.environment == "production":
            if not self.cookie_secure or not self.cors_allowed_origins:
                raise ValueError("Production requires Secure cookies and CORS origins")
            if any(not o.startswith("https://") for o in self.cors_allowed_origins):
                raise ValueError("Production origins must use HTTPS")
            url = make_url(self.database_url.get_secret_value())
            if url.query.get("sslmode", "require") not in (
                "require",
                "verify-ca",
                "verify-full",
            ):
                raise ValueError("Production PostgreSQL requires TLS")
            if "sslmode" not in url.query:
                url = url.update_query_dict({"sslmode": "require"})
                self.database_url = SecretStr(url.render_as_string(hide_password=False))
        return self

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 bytes")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from None
        if url.drivername in ("postgres", "postgresql"):
            url = url.set(drivername="postgresql+psycopg")
        if url.drivername != "postgresql+psycopg" or not url.host or not url.database:
            raise ValueError(
                "DATABASE_URL requires postgresql+psycopg, host and database"
            )
        return SecretStr(url.render_as_string(hide_password=False))
