"""Exercise the release smoke against real disposable PostgreSQL before live use."""

from fastapi.testclient import TestClient

from app.main import create_app
from scripts.smoke_subjects import register, subjects


def test_release_smoke_success_path(pg_settings):
    report = {"checks": {}}
    with (
        TestClient(create_app(pg_settings), base_url="https://testserver") as a,
        TestClient(create_app(pg_settings), base_url="https://testserver") as b,
    ):
        first = register(a, "A", report)
        second = register(b, "B", report)
        assert first != second
        subjects(a, b, report, 204)
        assert report["delete"] == "passed: HTTP 204"
        for client in (a, b):
            assert (
                client.post(
                    "/api/v1/auth/logout",
                    headers={"X-CSRF-Token": client.cookies.get("cognova_csrf")},
                ).status_code
                == 204
            )
