from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.settings import Settings
from app.main import create_app
from app.services.readiness_service import ReadinessService


def test_liveness_does_not_connect_to_database():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        with patch.object(client.app.state.database, "session") as session:
            response = client.get("/api/v1/health")
        session.assert_not_called()
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"


def test_readiness_unavailable_does_not_expose_database_details():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        with patch.object(
            ReadinessService,
            "check",
            side_effect=OperationalError(
                "secret-query",
                {},
                Exception("private-host-and-password"),
            ),
        ):
            response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "private" not in response.text


def test_readiness_requires_current_migration():
    database = MagicMock()
    session = database.session.return_value.__enter__.return_value
    session.scalar.return_value = 1
    session.scalars.return_value.all.return_value = ["0001_create_users"]
    assert not ReadinessService(database).check()
    session.scalars.return_value.all.return_value = ["0004_subjects"]
    assert ReadinessService(database).check()


@pytest.mark.parametrize(
    "revisions",
    [
        [],
        ["0002_auth_sessions"],
        ["0003_unknown"],
        ["0004_subjects", "another_head"],
    ],
)
def test_missing_unknown_or_multiple_heads_fail_closed(revisions):
    database = MagicMock()
    session = database.session.return_value.__enter__.return_value
    session.scalar.return_value = 1
    session.scalars.return_value.all.return_value = revisions
    assert not ReadinessService(database).check()
