from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import create_app


def test_openapi_does_not_advertise_unimplemented_endpoints():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Cognova API"
    assert response.json()["paths"] == {}


def test_cors_allows_configured_origin_and_bearer_header():
    settings = Settings(_env_file=None, cors_origins=["http://localhost:5173"])
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
