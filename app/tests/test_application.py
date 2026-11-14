import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.api.auth_dependencies import check_origin
from app.core.auth_error import AuthError
from app.core.settings import Settings
from app.main import create_app


def test_openapi_does_not_advertise_unimplemented_endpoints():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Cognova API"
    assert set(response.json()["paths"]) == {
        "/api/v1/calendar",
        "/api/v1/analysis/behavior",
        "/api/v1/analytics/overview",
        "/api/v1/analytics/study-time",
        "/api/v1/analytics/timeline",
        "/api/v1/analytics/search",
        "/api/v1/study-plans",
        "/api/v1/study-plans/generate",
        "/api/v1/study-plans/{plan_id}",
        "/api/v1/study-plans/{plan_id}/accept",
        "/api/v1/study-plans/{plan_id}/reject",
        "/api/v1/study-plans/{plan_id}/regenerate",
        "/api/v1/study-plans/{plan_id}/activate",
        "/api/v1/study-plans/{plan_id}/complete",
        "/api/v1/study-plans/{plan_id}/abandon",
        "/api/v1/study-plans/{plan_id}/undo",
        "/api/v1/study-plans/{plan_id}/challenges",
        "/api/v1/study-plans/{plan_id}/challenges/{challenge_id}",
        "/api/v1/study-plans/{plan_id}/challenges/{challenge_id}/start",
        "/api/v1/study-plans/{plan_id}/challenges/{challenge_id}/complete",
        "/api/v1/study-plans/{plan_id}/challenges/{challenge_id}/fail",
        "/api/v1/study-plans/{plan_id}/challenges/{challenge_id}/cancel",
        "/api/v1/sessions",
        "/api/v1/sessions/{session_id}",
        "/api/v1/sessions/{session_id}/start",
        "/api/v1/sessions/{session_id}/pause",
        "/api/v1/sessions/{session_id}/resume",
        "/api/v1/sessions/{session_id}/finish",
        "/api/v1/activities",
        "/api/v1/activities/{activity_id}",
        "/api/v1/activities/{activity_id}/status",
        "/api/v1/activities/{activity_id}/deadline",
        "/api/v1/activities/{activity_id}/deadline-history",
        "/api/v1/subjects",
        "/api/v1/subjects/catalog",
        "/api/v1/subjects/{subject_id}",
        "/api/v1/subjects/{subject_id}/archive",
        "/api/v1/subjects/{subject_id}/reactivate",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/sessions",
        "/api/v1/auth/sessions/{session_id}",
        "/api/v1/health",
        "/api/v1/ready",
        "/api/v1/onboarding/academic-profile",
        "/api/v1/questionnaire",
        "/api/v1/questionnaire/catalog",
        "/api/v1/questionnaire/history",
    }


def test_cors_allows_configured_origin_and_bearer_header():
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    settings = Settings(_env_file=None, cors_allowed_origins=origins)
    with TestClient(create_app(settings)) as client:
        responses = [
            client.options(
                "/api/v1/subjects",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Authorization,Content-Type",
                },
            )
            for origin in origins
        ]
        rejected = client.options(
            "/api/v1/subjects",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )
    for response, origin in zip(responses, origins, strict=True):
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:8080", "http://127.0.0.1:8080"],
)
def test_origin_guard_accepts_explicit_local_origins(origin):
    app = create_app(
        Settings(
            _env_file=None,
            cors_allowed_origins=[
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ],
        )
    )
    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/auth/register",
            "raw_path": b"/api/v1/auth/register",
            "query_string": b"",
            "headers": [(b"origin", origin.encode("ascii"))],
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8080),
            "app": app,
        }
    )
    check_origin(request)


def test_origin_guard_still_rejects_unlisted_origin():
    app = create_app(
        Settings(
            _env_file=None,
            cors_allowed_origins=[
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ],
        )
    )
    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/auth/register",
            "raw_path": b"/api/v1/auth/register",
            "query_string": b"",
            "headers": [(b"origin", b"https://untrusted.example")],
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8080),
            "app": app,
        }
    )
    with pytest.raises(AuthError) as error:
        check_origin(request)
    assert error.value.code == "FORBIDDEN"
