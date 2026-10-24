from fastapi.testclient import TestClient

from app.main import create_app
from scripts.smoke_activities import activities, logout, register


def test_activities_release_smoke_with_postgresql(pg_settings):
    report = {"checks": {}}
    with (
        TestClient(create_app(pg_settings), base_url="https://testserver") as a,
        TestClient(create_app(pg_settings), base_url="https://testserver") as b,
    ):
        assert register(a, "A", report) != register(b, "B", report)
        activities(a, b, report)
        logout(a, "A", report)
        logout(b, "B", report)
    assert report["history_preserved"]
    assert report["checks"]["concurrent 409"]["code"] == "ACTIVITY_DEADLINE_CONFLICT"
