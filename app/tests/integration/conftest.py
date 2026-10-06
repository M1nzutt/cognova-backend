import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.settings import Settings
from app.database.database import Database
from app.main import create_app


@pytest.fixture
def pg_settings():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration")
    Settings(_env_file=None, database_url=url)  # Reject non-PostgreSQL URLs.
    schema = "test_" + uuid4().hex
    admin = create_engine(
        url, hide_parameters=True, connect_args={"connect_timeout": 5}
    )
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    scoped_url = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
    engine = create_engine(
        scoped_url, hide_parameters=True, connect_args={"connect_timeout": 5}
    )
    try:
        config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield Settings(
            _env_file=None,
            database_url=scoped_url.render_as_string(hide_password=False),
        )
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


@pytest.fixture
def client(pg_settings):
    with TestClient(create_app(pg_settings), base_url="https://testserver") as client:
        yield client


@pytest.fixture
def database(pg_settings):
    database = Database(pg_settings)
    yield database
    database.dispose()


@pytest.fixture
def registration():
    return {
        "name": "Sara",
        "email": "sara@example.com",
        "password": "Example123!",
        "degree_program": "Ingeniería de Software",
        "semester": 4,
        "academic_goal": "Mejorar mi constancia",
    }
