from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.onboarding_dependencies import get_onboarded_user
from app.api.study_sessions import get_service
from app.core.settings import Settings
from app.main import create_app
from app.schemas.study_session_list_response import StudySessionListResponse


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


def test_session_list_parses_limit_from_query_string():
    class StubService:
        def list(self, user_id, filters):
            self.requested = filters
            return StudySessionListResponse(items=[], next_cursor=None)

    service = StubService()
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_onboarded_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/sessions",
            params={
                "limit": "2",
                "subject_id": "3",
                "activity_id": "5",
                "after_planned_start_at": "2030-01-01T00:00:00Z",
                "after_id": "7",
            },
        )

    assert response.status_code == 200
    assert service.requested.limit == 2
    assert service.requested.subject_id == 3
    assert service.requested.activity_id == 5
    assert service.requested.after_id == 7
    assert response.headers["cache-control"] == "no-store"
