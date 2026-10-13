import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.settings import Settings
from app.database.database import Database
from app.main import create_app
from app.tests.database_tooling import database_checkout, migrate_test_schema


@pytest.fixture
def pg_settings():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("REQUIRE_POSTGRES_TESTS") == "1":
            pytest.fail("CI requires TEST_DATABASE_URL")
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration")
    if os.environ.get("TEST_DATABASE_ALLOW_DDL") != "yes":
        pytest.fail("Explicit TEST_DATABASE_ALLOW_DDL=yes required for disposable DB")
    Settings(_env_file=None, database_url=url)  # Reject non-PostgreSQL URLs.
    parsed = make_url(url)
    if parsed.host not in {"localhost", "127.0.0.1", "::1"} or parsed.query:
        pytest.fail("Use local disposable PostgreSQL without URL options or tunnels")
    checkout = database_checkout()
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
        migrate_test_schema(checkout, scoped_url.render_as_string(hide_password=False))
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
    }
