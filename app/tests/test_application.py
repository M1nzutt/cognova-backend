from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import create_app


def test_openapi_does_not_advertise_unimplemented_endpoints():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Cognova API"
    assert set(response.json()["paths"]) == {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/sessions",
        "/api/v1/auth/sessions/{session_id}",
        "/api/v1/health",
        "/api/v1/ready",
    }


def test_cors_allows_configured_origin_and_bearer_header():
    settings = Settings(_env_file=None, cors_allowed_origins=["http://localhost:5173"])
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/api/v1/subjects",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )
        rejected = client.options(
            "/api/v1/subjects",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
