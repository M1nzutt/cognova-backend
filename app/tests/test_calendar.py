from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.api.calendar import get_service
from app.api.onboarding_dependencies import get_onboarded_user
from app.core.settings import Settings
from app.main import create_app
from app.schemas.calendar_filters import CalendarFilters
from app.services.calendar_service import CalendarService

WINDOW = {
    "deadline_from": "2030-01-01T00:00:00Z",
    "deadline_to": "2030-02-01T00:00:00Z",
}


@pytest.mark.parametrize(
    "change",
    [
        {"deadline_from": "2030-01-01"},
        {"deadline_from": "2030-01-01T00:00:00"},
        {"deadline_from": "1893456000"},
        {"deadline_to": WINDOW["deadline_from"]},
        {"deadline_to": "2029-12-31T00:00:00Z"},
        {"deadline_to": "2031-01-03T00:00:00Z"},
        {"after_id": 1},
        {"after_deadline": WINDOW["deadline_from"]},
        {"after_id": 1, "after_deadline": WINDOW["deadline_to"]},
        {"after_id": 1, "after_deadline": "2029-01-01T00:00:00Z"},
        {"limit": 0},
        {"limit": 101},
        {"subject_id": 0},
        {"status": "done"},
        {"priority": "critical"},
        {"user_id": 2},
    ],
)
def test_invalid_window(change):
    with pytest.raises(ValidationError):
        CalendarFilters(**{**WINDOW, **change})


def test_range_uses_instants_and_accepts_maximum():
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    f = CalendarFilters(deadline_from=start, deadline_to=start + timedelta(days=366))
    assert f.limit == 50
    with pytest.raises(ValidationError):
        CalendarFilters(
            deadline_from="2030-01-01T12:00:00Z",
            deadline_to="2030-01-01T07:00:00-05:00",
        )


def test_openapi_read_only_and_contract():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        spec = client.get("/openapi.json").json()
    path = spec["paths"]["/api/v1/calendar"]
    assert set(path) == {"get"}
    op = path["get"]
    assert op["security"]
    assert {"200", "401", "403", "422", "503"} <= op["responses"].keys()
    params = {p["name"]: p for p in op["parameters"]}
    assert set(params) == {
        "deadline_from",
        "deadline_to",
        "subject_id",
        "status",
        "priority",
        "limit",
        "after_deadline",
        "after_id",
    }
    assert params["deadline_from"]["required"] and params["deadline_to"]["required"]
    item = spec["components"]["schemas"]["CalendarActivityItem"]["properties"]
    assert set(item) == {
        "id",
        "type",
        "title",
        "subject_id",
        "deadline",
        "original_deadline",
        "priority",
        "status",
        "estimated_duration",
    }
    assert item["type"]["const"] == "activity"


def test_db_failure_is_sanitized_and_not_retried():
    app = create_app(Settings(_env_file=None))
    service = MagicMock()
    service.list.side_effect = OperationalError("private SQL", {}, Exception("secret"))
    app.dependency_overrides[get_onboarded_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as client:
        response = client.get("/api/v1/calendar", params=WINDOW)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "secret" not in response.text and "SQL" not in response.text
    assert response.headers["cache-control"] == "no-store"
    service.list.assert_called_once()


def test_empty_service_performs_only_bounded_select():
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    assert CalendarService(db).list(7, CalendarFilters(**WINDOW)).model_dump() == {
        "items": [],
        "next_cursor": None,
    }
    statement = db.scalars.call_args.args[0]
    assert statement.is_select and statement.compile().params["user_id_1"] == 7
    assert 51 in statement.compile().params.values()
    db.commit.assert_not_called()
    db.execute.assert_not_called()
    db.add.assert_not_called()
