import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    # Unit tests never use the developer's database or .env credentials.
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/cognova_test"
    )
    monkeypatch.setenv("CORS_ORIGINS", "[]")
