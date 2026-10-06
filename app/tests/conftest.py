import secrets

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    # Unit tests never use the developer's database or .env credentials.
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/cognova_test"
    )
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "[]")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("JWT_SECRET", secrets.token_urlsafe(48))
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("AUTH_RATE_LIMIT", "20")
