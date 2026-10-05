import secrets

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    # Unit tests never use the developer's database or .env credentials.
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/cognova_test"
    )
    monkeypatch.setenv("CORS_ORIGINS", "[]")
    monkeypatch.setenv("JWT_SECRET", secrets.token_urlsafe(48))
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")
