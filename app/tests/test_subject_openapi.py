from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import create_app


def test_subject_contract_is_published_with_security_and_exact_dtos():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    expected = {
        "/api/v1/subjects": {"get", "post"},
        "/api/v1/subjects/catalog": {"get"},
        "/api/v1/subjects/{subject_id}": {"get", "put", "delete"},
        "/api/v1/subjects/{subject_id}/archive": {"post"},
        "/api/v1/subjects/{subject_id}/reactivate": {"post"},
    }
    for path, methods in expected.items():
        assert set(paths[path]) == methods
        for method in methods:
            operation = paths[path][method]
            assert operation["security"] == [{"HTTPBearer": []}]
            assert {"401", "403", "404", "409", "422", "503"} <= set(
                operation["responses"]
            )
    models = schema["components"]["schemas"]
    fields = {"name", "difficulty", "color_base", "color_shade"}
    assert set(models["SubjectWrite"]["required"]) == fields
    assert set(models["SubjectWrite"]["properties"]) == fields
    assert set(models["SubjectCreate"]["properties"]) == fields | {"status"}
    assert models["SubjectCreate"]["additionalProperties"] is False
    assert models["SubjectCreate"]["properties"]["name"]["maxLength"] == 20
    assert set(models["SubjectResponse"]["properties"]) == fields | {
        "id",
        "status",
        "created_at",
        "updated_at",
    }
    delete = paths["/api/v1/subjects/{subject_id}"]["delete"]
    confirm = next(p for p in delete["parameters"] if p["name"] == "confirm")
    assert confirm["required"] and confirm["schema"]["const"] == "true"
    assert "content" not in delete["responses"]["204"]
