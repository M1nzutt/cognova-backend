from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import create_app


def test_activities_openapi_matches_public_contract():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    paths = spec["paths"]
    for suffix, methods in [
        ("", ["get", "post"]),
        ("/{activity_id}", ["get", "put", "delete"]),
        ("/{activity_id}/status", ["patch"]),
        ("/{activity_id}/deadline", ["patch"]),
        ("/{activity_id}/deadline-history", ["get"]),
    ]:
        for method in methods:
            op = paths["/api/v1/activities" + suffix][method]
            assert op["security"]
            assert {"401", "403", "404", "409", "422", "503"} <= op["responses"].keys()
    schemas = spec["components"]["schemas"]
    assert schemas["ActivityWrite"]["additionalProperties"] is False
    assert "user_id" not in schemas["ActivityResponse"]["properties"]
    assert schemas["ActivityWrite"]["properties"]["title"]["maxLength"] == 50
    assert schemas["ActivityWrite"]["properties"]["deadline"]["format"] == "date-time"
    delete = paths["/api/v1/activities/{activity_id}"]["delete"]
    assert "content" not in delete["responses"]["204"]
    confirmation = next(p for p in delete["parameters"] if p["name"] == "confirm")
    assert confirmation["required"] and confirmation["schema"]["const"] == "true"
    query = {p["name"] for p in paths["/api/v1/activities"]["get"]["parameters"]}
    assert {
        "subject_id",
        "status",
        "priority",
        "deadline",
        "deadline_from",
        "deadline_to",
        "limit",
        "after_id",
    } == query
