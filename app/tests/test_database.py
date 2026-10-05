from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.core.settings import Settings
from app.database.database import Database
from app.main import create_app


@pytest.mark.parametrize(
    "url", ["sqlite:///local.db", "not-a-url", "postgresql+psycopg://localhost"]
)
def test_rejects_invalid_database_configuration(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=url)


def test_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_secret_is_hidden():
    settings = Settings(_env_file=None)
    assert "test:test" not in repr(settings)


def test_database_lifecycle_and_sessions_do_not_connect_at_startup():
    settings = Settings(_env_file=None)
    with patch("app.database.database.create_engine") as create_engine:
        with TestClient(create_app(settings)) as client:
            database = client.app.state.database
            with database.session() as first, database.session() as second:
                assert first is not second
            create_engine.return_value.connect.assert_not_called()
            create_engine.return_value.dispose.assert_not_called()
        create_engine.return_value.dispose.assert_called_once()


def test_failed_unit_of_work_rolls_back_and_closes():
    database = Database(Settings(_env_file=None))
    session = MagicMock()
    session.__enter__.return_value = session
    try:
        with patch.object(database, "_session_factory", return_value=session):
            with pytest.raises(RuntimeError, match="failed operation"):
                with database.session():
                    raise RuntimeError("failed operation")
        session.rollback.assert_called_once()
        session.__exit__.assert_called_once()
        session.commit.assert_not_called()
    finally:
        database.dispose()


def test_postgresql_connection_when_explicitly_configured(monkeypatch):
    """Optional integration smoke test; performs only SELECT 1."""
    import os

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to check a real PostgreSQL instance")
    database = Database(Settings(_env_file=None, database_url=url))
    try:
        with database.session() as session:
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        database.dispose()
