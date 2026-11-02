from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import create_app


def test_study_session_openapi_exposes_only_contract_routes():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        spec = client.get("/openapi.json").json()

    paths = spec["paths"]
    session_paths = {
        path: paths[path] for path in paths if path.startswith("/api/v1/sessions")
    }
    assert set(session_paths) == {
        "/api/v1/sessions",
        "/api/v1/sessions/{session_id}",
        "/api/v1/sessions/{session_id}/start",
        "/api/v1/sessions/{session_id}/pause",
        "/api/v1/sessions/{session_id}/resume",
        "/api/v1/sessions/{session_id}/finish",
    }
    assert set(session_paths["/api/v1/sessions"]) == {"get", "post"}
    assert set(session_paths["/api/v1/sessions/{session_id}"]) == {
        "get",
        "put",
        "delete",
    }
    for action in ("start", "pause", "resume", "finish"):
        assert set(session_paths[f"/api/v1/sessions/{{session_id}}/{action}"]) == {
            "post"
        }
    delete = session_paths["/api/v1/sessions/{session_id}"]["delete"]
    confirm = next(p for p in delete["parameters"] if p["name"] == "confirm")
    assert confirm["required"] is True
    assert "user_id" not in str(spec["components"]["schemas"])
    assert "StudySessionDetail" in spec["components"]["schemas"]
    assert "StudySessionListResponse" in spec["components"]["schemas"]
